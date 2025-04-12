"""
pdf_extractor.py
Module for extracting text from PDF files using pdfplumber.
"""

import pdfplumber
import logging
from pathlib import Path

def extract_text_from_pdf(pdf_file_path: str) -> str:
    """
    Extract all text from a PDF file.

    :param pdf_file_path: str, path to the PDF file.
    :return: str, the extracted text content from the PDF.
    """
    pdf_path = Path(pdf_file_path)
    if not pdf_path.is_file():
        logging.error(f"PDF file not found: {pdf_file_path}")
        return ""

    all_text = []
    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # text 可能为空, 如果当前页面没能抽取出任何可识别的文字
                if text:
                    all_text.append(text)
        combined_text = "\n".join(all_text)
        logging.info(f"Extracted text from {pdf_file_path}, length: {len(combined_text)} characters.")
        return combined_text

    except Exception as e:
        logging.error(f"Error while reading PDF {pdf_file_path}: {e}")
        return ""
