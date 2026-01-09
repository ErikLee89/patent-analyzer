# Patent Analyzer | 专利分析工具

## Overview | 概述
This is a specialized skill for Gemini CLI to analyze patent PDF files (CN, US, EP, KR, etc.) using a hybrid strategy.
这是一个专为 Gemini CLI 设计的技能，用于采用混合策略分析专利 PDF 文件（包括中国、美国、欧洲、韩国等）。

## Key Features | 核心功能
- **Multi-language Support**: Extracts metadata from patents in various languages (CN, US, EP, JP, KR) using international standard INID codes.
- **多语言支持**：利用国际标准的 INID 代码提取各种语言专利（中、美、欧、日、韩）的元数据。
- **Hybrid Extraction**: Fast text extraction for text-based PDFs and Gemini Vision fallback for scanned/image-based PDFs.
- **混合提取**：针对文本型 PDF 进行快速文本提取，针对扫描/图片型 PDF 自动调用 Gemini 视觉能力。
- **Compact Bilingual Output**: Automatically generates English-Chinese bilingual content for titles, abstracts, and claims in a compact format.
- **紧凑型双语输出**：自动为标题、摘要和权利要求生成中英文对照内容，格式美观。
- **Clean Workspace Rules**: All results and temporary files are stored directly in the patent source folder, keeping the skill directory clean.
- **路径隔离规则**：所有结果和临时文件都直接存储在专利源文件夹中，确保技能目录不被污染。

## Installation | 安装
1. Clone this repository into your Gemini skills directory.
   将此仓库克隆到您的 Gemini skills 目录中。
2. Install dependencies:
   安装依赖：
   ```bash
   pip install pdfplumber pandas openpyxl
   ```

## Usage | 使用
1. Navigate to your patent folder:
   在终端进入您的专利文件夹：
   ```bash
   cd /path/to/your/patents
   ```
2. Call the skill:
   调用技能：
   `patent-analyzer`

## Maintenance | 维护
Once the skill is stable, do not modify the core logic files unless fixing critical bugs.
技能稳定后，除非修复重大 Bug，否则请勿修改核心逻辑文件。
