# main.py

import sys
import os
import logging
from pathlib import Path

# 导入提取器
from ingestion.pdf_extractor import extract_text_from_pdf
from ingestion.docx_extractor import extract_text_from_docx
from ingestion.excel_extractor import extract_data_from_excel

# 导入清洗器
from ingestion.cleaners import clean_text, normalize_text, clean_row

logging.basicConfig(level=logging.INFO)

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <file1> <file2> ...")
        sys.exit(1)

    output_dir = Path("data/extracted")
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_path in sys.argv[1:]:
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()

        if not path_obj.exists():
            logging.error(f"File not found: {file_path}")
            continue

        if ext == ".pdf":
            raw_text = extract_text_from_pdf(file_path)
            # 调用清洗
            cleaned = clean_text(raw_text)
            # 可选：再做 normalization
            normalized = normalize_text(cleaned)

            out_file = output_dir / (path_obj.stem + ".txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(normalized)
            logging.info(f"Saved PDF text to {out_file}")

        elif ext == ".docx":
            raw_text = extract_text_from_docx(file_path)
            # 同样清洗
            cleaned = clean_text(raw_text)
            normalized = normalize_text(cleaned)

            out_file = output_dir / (path_obj.stem + ".txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(normalized)
            logging.info(f"Saved DOCX text to {out_file}")

        elif ext == ".xlsx":
            rows = extract_data_from_excel(file_path)

            # 逐行清洗
            cleaned_rows = []
            for row in rows:
                if not row:
                    continue
                # 用 clean_row
                c_row = clean_row(row)
                cleaned_rows.append(c_row)

            # 写到 .txt（或 CSV）
            out_file = output_dir / (path_obj.stem + "_table.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                for r in cleaned_rows:
                    # 把列表 join 成文本, 用逗号隔开
                    line = ",".join(r)
                    f.write(line + "\n")

            logging.info(f"Saved Excel data to {out_file}")
        else:
            logging.warning(f"Unsupported file extension '{ext}' for {file_path}. Skipping.")

if __name__ == "__main__":
    main()
