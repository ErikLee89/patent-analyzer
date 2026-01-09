---
name: patent-analyzer
description: Analyzes patent PDF files using a hybrid approach (Text extraction + Gemini Vision fallback) to extract metadata and content, organizing them into a formatted Excel report.
---

# Patent Analyzer

## Overview

This skill organizes and analyzes patent PDF files. It employs a **hybrid strategy**:
1.  **Fast Path**: Attempts to extract text directly from PDF. If successful, parses metadata using Regex.
2.  **Vision Path**: If text extraction fails (scanned PDF), flags the file for Gemini to process visually.

## Workflow

1.  **Batch Scan & Text Extraction**:
    - The Agent runs `scripts/batch_process.py`.
    - It tries to extract text using `pdfplumber`.
    - **Metadata Extraction**:
        - **Applicant**: Match `(71)申请人` OR `(73)专利权人`.
        - **Column Order**: 专利号, 标题, 申请人, 发明人, IPC分类号, 申请日, 授权日, Summary, 摘要, 主权项.

2.  **Vision Processing (Agent Loop)**:
    - For scanned PDFs, the Agent calls `read_file` and visually extracts information, prioritizing `(73)专利权人` if `(71)` is absent.

3.  **Finalize & Format**:
    - The Agent runs `scripts/save_report.py`.
    - **Sorting**: By "专利号".
    - **Column Widths (Adjusted for Excel padding)**:
        - 标题, 申请人, 发明人: 15.75 (Target 15)
        - Summary: 20.75 (Target 20)
        - 摘要, 主权项: 80.75 (Target 80)
    - **Formatting**: Word wrap, Top alignment.

## Data Structure (JSON)
```json
{
  "专利号": "CN xxxxxxxxx B",
  "标题": "用于XXXX的推进系统",
  "申请人": "XXXX有限公司",
  "发明人": "XXX...",
  "IPC分类号": "B63H 9/02",
  "申请日": "2014.11.11",
  "授权日": "2019.01.18",
  "Summary": "一句话总结...",
  "摘要": "完整摘要文本...",
  "主权项": "第一条权利要求..."
}
```
