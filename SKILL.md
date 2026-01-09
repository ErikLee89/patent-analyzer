---
name: patent-analyzer
description: Analyzes patent PDF files using a hybrid approach (Text extraction + Gemini Vision fallback) to extract metadata and content, organizing them into a formatted Excel report.
---

# Patent Analyzer

## Overview

This skill organizes and analyzes patent PDF files (CN, US, EP, KR, etc.). It employs a **hybrid strategy**:
1.  **Fast Path**: Attempts to extract text directly from PDF using `batch_process.py` with multi-language INID support.
2.  **Vision Path**: If text extraction fails (scanned PDF/images), flags the file for the Agent to process visually.

## Path Constraints (CRITICAL)
-   **No Pollution**: **ALL** temporary files (JSONs, lists) and final reports **MUST** be created inside the **user-provided target directory** (the directory containing the PDFs).
-   **Clean Skill**: **DO NOT** create any files in the `skills/patent-analyzer` directory or its subdirectories during execution.

## Workflow

1.  **Batch Scan & Text Extraction**:
    -   The Agent runs `scripts/batch_process.py --input <TARGET_DIR>`.
    -   **Output**: The script automatically saves `patent_data.json` and `needs_vision.json` inside `<TARGET_DIR>`.

2.  **Vision Processing (Agent Loop)**:
    -   The Agent reads `<TARGET_DIR>/needs_vision.json`.
    -   For each file listed, the Agent calls `read_file` (page 1) and visually extracts information.
    -   **Translation Requirement**: For **Foreign Patents**, the Agent **MUST** provide the extracted content in a **Bilingual Format** (English/Original followed immediately by Chinese Translation, **NO blank line**) for the following fields:
        -   **标题 (Title)**
        -   **摘要 (Abstract)**
        -   **Summary**
        -   **主权项 (Claims)**
    -   *Format Example*:
        ```text
        Method for damping motions of a vessel...
        一种用于阻尼船舶运动的方法...
        ```
    -   *Note*: Do NOT translate Applicant or Inventor names.
    -   **Save Location**: The Agent saves the extracted vision data to `<TARGET_DIR>/temp_vision_data.json`.

3.  **Finalize & Format**:
    -   The Agent runs `scripts/save_report.py <TARGET_DIR>/patent_data.json <TARGET_DIR>/report.xlsx`.
    -   (If vision data exists, merge it appropriately or handle separate reports as requested).

## Data Structure (JSON)
```json
{
  "专利号": "US 10,099,762 B2",
  "标题": "METHOD OF MANUFACTURING...\n制造...的方法",
  "申请人": "Norsepower Oy Ltd",
  "发明人": "Jarkko Väinämö...",
  "IPC分类号": "B63H 9/02",
  "申请日": "2016.09.16",
  "授权日": "2018.10.16",
  "Summary": "A method is provided...\n提供了一种方法...",
  "摘要": "A method is provided for manufacturing...\n提供了一种制造...的方法...",
  "主权项": "1. A method of manufacturing...\n1. 一种制造...的方法..."
}
```

## Maintenance Rules
-   **Stable State**: This skill is considered stable. **DO NOT modify** the skill files (`batch_process.py`, `save_report.py`, `SKILL.md`) unless explicitly requested to fix a critical bug.
-   **Adaptability**: Favor using the Agent's cognitive capabilities (e.g., for translation, filtering, or handling new layouts) over modifying the core Python scripts.
