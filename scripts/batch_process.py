import pdfplumber
import re
import json
import os
import glob

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_filename(filename):
    """
    Minimal parsing for backup.
    """
    info = {"文件名": filename}
    try:
        name = os.path.splitext(filename)[0]
        # Basic check if it starts with CN
        if name.startswith("CN"):
            parts = name.split(" ")
            if len(parts) > 1:
                info["专利号"] = parts[0] + " " + parts[1]
    except:
        pass
    return info

def extract_patent_info(file_path):
    filename = os.path.basename(file_path)
    
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
            # Check for scanned PDF: if page 1 has very little text
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text or len(first_page_text) < 50:
                return None # Signal as Scanned PDF

            # Read first 3 pages
            for page in pdf.pages[:3]: 
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # Normalize text
        text = text.replace('（', '(').replace('）', ')').replace('：', ':')
        
        # Regex Helpers
        def find_val(pattern, txt):
            m = re.search(pattern, txt)
            return clean_text(m.group(1)) if m else ""

        # Metadata Extraction
        info["专利号"] = find_val(r'\(10\)\s*(?:授权公告号|申请公布号|公告号|公开号)\s*(CN\s*\d+(\s[A-Z])?)', text)
        info["标题"] = find_val(r'\(54\)\s*(?:发明名称|实用新型名称)\s*(.*?)(\n|\r|\(\d+\))', text)
        info["申请人"] = find_val(r'\(71\)\s*申请人\s*(.*?)(\n|\r|\(\d+\))', text)
        if not info["申请人"]:
            info["申请人"] = find_val(r'\(73\)\s*专利权人\s*(.*?)(\n|\r|\(\d+\))', text)
        info["发明人"] = find_val(r'\(72\)\s*发明人\s*(.*?)(\n|\r|\(\d+\))', text)
        info["申请日"] = find_val(r'\(22\)\s*申请日\s*(\d{4}\.\d{1,2}\.\d{1,2})', text)
        info["授权日"] = find_val(r'\(45\)\s*授权公告日\s*(\d{4}\.\d{1,2}\.\d{1,2})', text)
        info["IPC分类号"] = find_val(r'\(51\)\s*Int\.? ?Cl\.?\s*([A-Z]\d+[A-Z]\s*\d+/\d+)', text)

        # Abstract
        if "(57)摘要" in text:
            start = text.find("(57)摘要") + len("(57)摘要")
            cand = text[start:start+800]
            lines = cand.split('\n')
            abs_text = ""
            for line in lines:
                if not line.strip(): continue
                if re.match(r'^\(\d+\)', line.strip()): break
                abs_text += line.strip()
            info["摘要"] = abs_text[:500]
            
            # Summary (First sentence)
            sentences = re.split(r'[。.]', abs_text)
            if sentences: info["Summary"] = sentences[0] + "。"
            if len(info["Summary"]) > 60: info["Summary"] = info["Summary"][:60] + "..."

        # Claim 1
        if "权利要求书" in text:
            start = text.find("权利要求书")
            c_text = text[start:start+2000]
            match = re.search(r'1\s*[.、]\s*(.*?)(?=\n\s*2\s*[.、]|$)', c_text, re.DOTALL)
            if match:
                info["主权项"] = clean_text(match.group(1))[:500]
            else:
                # Fallback: first non-header line
                lines = c_text.split('\n')
                header_passed = False
                for line in lines:
                    if "权利要求书" in line: header_passed = True; continue
                    if header_passed and line.strip():
                        info["主权项"] = line.strip()[:500]
                        break

        # Double check: if critical info missing, treat as scanned?
        # e.g. if Abstract is empty, it's likely parsing failed or layout is complex (image-based)
        if not info["摘要"] or not info["主权项"]:
             # If we have title and applicant, we might keep it.
             # But user wants high quality. Let's send to vision if abstract is missing.
             if not info["标题"]:
                 return None
    
    except Exception as e:
        print(f"Error: {e}")
        return None

    return info

def main():
    target_dir = "."
    output_json = "temp_vision_data.json"
    vision_list = "needs_vision.json"
    
    files = glob.glob(os.path.join(target_dir, "*.pdf"))
    success_data = []
    failed_files = []
    
    print(f"Scanning {len(files)} files...")
    for i, f in enumerate(files):
        if i % 10 == 0: print(f"Processing {i}/{len(files)}")
        
        data = extract_patent_info(f)
        if data:
            success_data.append(data)
        else:
            failed_files.append(f)
            
    # Save Success Data
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(success_data, f, ensure_ascii=False, indent=2)
        
    # Save Failed List
    with open(vision_list, 'w', encoding='utf-8') as f:
        json.dump(failed_files, f, ensure_ascii=False, indent=2)
        
    print(f"\nSummary:")
    print(f"Text Extraction Success: {len(success_data)}")
    print(f"Needs Vision Processing: {len(failed_files)}")

if __name__ == "__main__":
    main()
