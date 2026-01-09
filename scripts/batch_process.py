import pdfplumber
import re
import json
import os
import glob
import argparse
import sys

def clean_text(text):
    if not text: return ""
    # Replace multiple spaces/newlines with single space, remove leading/trailing
    return re.sub(r'\s+', ' ', text).strip()

def extract_by_inid(text, inid_code, label_pattern=r'.*?'):
    """
    Extract content based on INID code (e.g., (54), (71)).
    Strategy:
    1. Find "(Code)".
    2. Skip optional label text (e.g., "Title", "发明名称") using label_pattern.
    3. Capture everything until the next INID code start "(XX)" or end of reasonable block.
    """
    # Pattern explanation:
    # (?:\(?\d{2}\)?) : Match (XX) or XX often used as INID. We focus on (Code).
    # We look for specific code, e.g., \(54\)
    # \s* : spaces
    # (?:label_pattern)? : Optional language specific label (e.g., "Applicant:")
    # \s*[:;.-]?\s* : separator
    # (.*?) : Content we want (lazy match)
    # (?=\n\s*\(?\d{2}\)?|\n\s*[A-Z][a-z]+:|$) : Lookahead for next INID code OR specific headers OR end of string
    
    # Heuristic: standard INID is (XX).
    # specific_pattern = r'\(' + inid_code + r'\)\s*(?:' + label_pattern + r')?\s*[:;]?\s*(.*?)(?=\n\s*\(\d{2}\)|\n\s*\(57\)|\Z)'
    
    # Simplified Robust Pattern:
    # Look for the INID code, ignore the immediate following characters until a "real" start, then grab text.
    # We assume the value is on the same line or following lines until the next (XX).
    
    pattern = r'\(' + inid_code + r'\)\s*[^:\n]*[:]?\s*(.*?)(?=\n\s*\(\d{2}\)|$)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1)
        # Post-cleaning: sometimes text includes the next tag if lookahead failed.
        # Check for any (XX) inside content and cut
        sub_match = re.search(r'\n\s*\(\d{2}\)', content)
        if sub_match:
            content = content[:sub_match.start()]
        return clean_text(content)
    return ""

def extract_patent_info(file_path):
    filename = os.path.basename(file_path)
    
    # Default schema (Keys matching save_report.py expectation)
    info = {
        "专利号": "",
        "标题": "",
        "申请人": "",
        "发明人": "",
        "IPC分类号": "",
        "申请日": "",
        "授权日": "",
        "摘要": "",
        "主权项": "",
        "Summary": "",
        "文件名": filename
    }

    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            # Check for scanned PDF
            if not pdf.pages: return None
            
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text or len(first_page_text) < 50:
                return None # Signal as Scanned PDF/Vision needed

            # Read first 3 pages (covers Front Page + Claims start usually)
            # Limit to avoid reading huge files entirely
            max_pages = min(len(pdf.pages), 5) 
            for page in pdf.pages[:max_pages]: 
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # Normalize text common issues
        text = text.replace('（', '(').replace('）', ')').replace('：', ':')
        
        # --- Extraction Logic ---

        # 1. Patent Number (10) / (11) / (12)
        # Try to find common patterns for ID
        # US: (10) Patent No.: US ...
        # CN: (10) 授权公告号 ...
        # Generic INID (10) or (11)
        p_num = extract_by_inid(text, "10", r"Patent No\.|授权公告号|Publicaiton Number")
        if not p_num:
            p_num = extract_by_inid(text, "11", r"Patent No\.|Publication Number")
        if not p_num:
            # Fallback: Top right corner usually has ID in US patents
            # or (12) often has "United States Patent" but sometimes number is near.
            # Let's try finding pattern "CC NNNNNNN K"
            pass 
        info["专利号"] = p_num

        # 2. Title (54)
        info["标题"] = extract_by_inid(text, "54", r"Title|发明名称|实用新型名称")
        
        # 3. Applicant (71) or Assignee (73)
        # US Patents often use (73) Assignee for the company. (71) is Applicant.
        # We prefer (73) if available (Owner), else (71).
        assignee = extract_by_inid(text, "73", r"Assignee|专利权人")
        applicant = extract_by_inid(text, "71", r"Applicant|申请人")
        
        info["申请人"] = assignee if assignee else applicant

        # 4. Inventors (72)
        info["发明人"] = extract_by_inid(text, "72", r"Inventors|发明人")

        # 5. Dates
        # (22) Filing Date
        info["申请日"] = extract_by_inid(text, "22", r"Filed|PCT Filed|申请日")
        # (45) Date of Patent (Grant) or (43) Pub Date
        grant_date = extract_by_inid(text, "45", r"Date of Patent|授权公告日")
        pub_date = extract_by_inid(text, "43", r"Pub\. Date|公布日")
        info["授权日"] = grant_date if grant_date else pub_date

        # 6. IPC/CPC (51)
        info["IPC分类号"] = extract_by_inid(text, "51", r"Int\. Cl\.|IPC")

        # 7. Abstract (57)
        # Sometimes "ABSTRACT" is a standalone header without (57) in US patents
        abs_text = extract_by_inid(text, "57", r"ABSTRACT|摘要")
        if not abs_text:
            # Fallback for US patents where ABSTRACT is a heading
            match = re.search(r'\n\s*ABSTRACT\s*\n(.*?)(?=\n\s*DRAWINGS|\n\s*1\.|\Z)', text, re.DOTALL | re.IGNORECASE)
            if match:
                 abs_text = clean_text(match.group(1))
        
        info["摘要"] = abs_text[:800] # Limit length

        # 8. Summary (First sentence of abstract)
        if abs_text:
            # Split by period (English) or full-stop (Chinese)
            sentences = re.split(r'[.。]', abs_text)
            if sentences:
                info["Summary"] = sentences[0] + ("." if "." in abs_text else "。")
                if len(info["Summary"]) > 100: info["Summary"] = info["Summary"][:100] + "..."

        # 9. Claims (Main Claim)
        # Heuristic: Find "Claims" or "What is claimed is" or "权利要求书"
        # Then look for "1." or "1、"
        claims_start_patterns = [r'What is claimed is:', r'Claims', r'权利要求书']
        c_text = ""
        for pat in claims_start_patterns:
            idx = text.find(pat)
            if idx != -1:
                # Grab a chunk after this header
                c_text = text[idx:idx+3000]
                break
        
        if c_text:
            # Look for Claim 1
            # 1. ...
            match = re.search(r'(?:\n|^)\s*1\s*[.、]\s*(.*?)(?=\n\s*2\s*[.、]|\Z)', c_text, re.DOTALL)
            if match:
                info["主权项"] = clean_text(match.group(1))[:800]
            else:
                 # Just take the first bit after header
                 info["主权项"] = clean_text(c_text[len(pat):])[:500]

        # --- Sanity Check / Fallback ---
        # If we missed Title and Applicant, it's likely parsing failed or format is non-standard.
        # But for "Foreign" files, we might be loose.
        if not info["标题"] and not info["申请人"]:
            # Last ditch: filename is usually reliable-ish in this user's case
            pass

    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return None

    return info

def main():
    parser = argparse.ArgumentParser(description="Batch process patent PDFs to extract metadata.")
    parser.add_argument("--input", "-i", default=".", help="Input directory containing PDF files.")
    parser.add_argument("--output", "-o", default="patent_data.json", help="Output JSON filename (saved in input directory).")
    
    args = parser.parse_args()
    
    target_dir = args.input
    if not os.path.exists(target_dir):
        print(f"Error: Input directory '{target_dir}' does not exist.")
        sys.exit(1)

    # Force outputs to be inside the target directory
    output_json_path = os.path.join(target_dir, os.path.basename(args.output))
    vision_list_path = os.path.join(target_dir, "needs_vision.json")
    
    # Recursive search for safety, or flat? specific requirement was a folder.
    # Let's do flat search in the target dir to avoid scanning subdirs unless asked.
    # But user might have folders. Let's stick to flat *.pdf in target_dir for now.
    search_pattern = os.path.join(target_dir, "*.pdf")
    files = glob.glob(search_pattern)
    
    success_data = []
    failed_files = []
    
    print(f"Target Directory: {os.path.abspath(target_dir)}")
    print(f"Scanning {len(files)} PDF files...")
    
    for i, f in enumerate(files):
        if i % 10 == 0: print(f"Processing {i}/{len(files)}...")
        
        data = extract_patent_info(f)
        if data:
            success_data.append(data)
        else:
            failed_files.append(f)
            
    # Save Success Data
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(success_data, f, ensure_ascii=False, indent=2)
        
    # Save Failed List
    with open(vision_list_path, 'w', encoding='utf-8') as f:
        json.dump(failed_files, f, ensure_ascii=False, indent=2)
        
    print(f"\nSummary:")
    print(f"Processed: {len(files)}")
    print(f"Success: {len(success_data)}")
    print(f"Needs Vision/Failed: {len(failed_files)}")
    print(f"Data saved to: {output_json_path}")
    print(f"Vision list saved to: {vision_list_path}")

if __name__ == "__main__":
    main()
