"""
excel_extractor.py
Module for extracting tabular data from Excel files using openpyxl.
"""

import openpyxl
import logging
from pathlib import Path

def extract_data_from_excel(excel_file_path: str) -> list:
    """
    Extract rows of data from an Excel file (first sheet).

    :param excel_file_path: str, path to the Excel (.xlsx) file
    :return: list of lists (each sub-list is a row of data)
    """
    xlsx_path = Path(excel_file_path)
    if not xlsx_path.is_file():
        logging.error(f"Excel file not found: {excel_file_path}")
        return []

    try:
        workbook = openpyxl.load_workbook(excel_file_path, data_only=True)
        sheet = workbook.active  # 默认使用第一个工作表
        rows_data = []
        for row in sheet.iter_rows(values_only=True):
            rows_data.append(row)
        logging.info(f"Extracted {len(rows_data)} rows from {excel_file_path}.")
        return rows_data

    except Exception as e:
        logging.error(f"Error reading Excel {excel_file_path}: {e}")
        return []
