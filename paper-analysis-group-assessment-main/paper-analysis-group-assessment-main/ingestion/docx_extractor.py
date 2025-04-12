"""
docx_extractor.py
Module for extracting text from DOCX files using python-docx.
"""

import docx
import logging
from pathlib import Path

def extract_text_from_docx(docx_file_path: str) -> str:
    """
    Extract all text from a DOCX file.

    :param docx_file_path: str, path to the DOCX file
    :return: str, the extracted text content
    """
    docx_path = Path(docx_file_path)
    if not docx_path.is_file():
        logging.error(f"DOCX file not found: {docx_file_path}")
        return ""

    try:
        doc = docx.Document(docx_file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        combined_text = "\n".join(paragraphs)
        logging.info(f"Extracted text from {docx_file_path}, length: {len(combined_text)} chars.")
        return combined_text

    except Exception as e:
        logging.error(f"Error reading DOCX {docx_file_path}: {e}")
        return ""
