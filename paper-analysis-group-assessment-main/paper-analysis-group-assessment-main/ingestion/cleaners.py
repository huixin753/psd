"""
cleaners.py
Module for data cleaning & normalization.

We provide:
1) clean_text()       -> Basic text-level cleaning
2) normalize_text()   -> Optional advanced normalization (like full-width to half-width, etc.)
3) clean_row()        -> For Excel row data cleaning
"""

import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Basic text cleaning steps:
    1) Strip leading/trailing whitespace
    2) Remove extra newlines
    3) Remove or replace weird unicode symbols (optional)
    4) Handle multiple spaces

    :param text: The raw text input
    :return: A cleaned version of the text
    """
    # 1) 去掉首尾空白
    text = text.strip()

    # 2) 把 Windows/Mac 的换行符统一成 \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3) 去掉多余换行（比如连续空行），保留一个空行
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # 4) 去掉多余空格（例如把多个连续空格变为1个）
    text = re.sub(r"[ \t]+", " ", text)

    return text


def normalize_text(text: str) -> str:
    """
    Advanced normalization:
    1) NFKC normalization: merge characters with diacritics, unify width
    2) Convert full-width characters (全角) to half-width (半角)
    3) Lowercase or uppercase if needed

    :param text: The cleaned text from clean_text()
    :return: A further normalized text
    """
    # 先做 Unicode 规范化
    text = unicodedata.normalize("NFKC", text)

    # 如果需要将文本强制转小写，可在这里加
    # text = text.lower()

    return text


def clean_row(row_data: list) -> list:
    """
    Clean each cell of a row from Excel or CSV.

    For example:
    1) Convert None -> "" (empty string)
    2) Convert numbers to string or unify numeric format
    3) Call clean_text() if it's string-based cell

    :param row_data: list of cells, e.g. [cell1, cell2, cell3...]
    :return: a cleaned list, same length
    """
    cleaned_cells = []
    for cell in row_data:
        if cell is None:
            # 如果是空值(None)，改为""
            cleaned_cells.append("")
        elif isinstance(cell, (int, float)):
            # 如果是数值，可以决定是否保留或转成字符串
            cleaned_cells.append(str(cell))
        elif isinstance(cell, str):
            # 如果是字符串，就用上面的 clean_text() 处理
            cell_text = clean_text(cell)
            # 也可以进一步 normalize_text(cell_text)
            cleaned_cells.append(cell_text)
        else:
            # 其它类型（比如日期、布尔值等）可自行决定如何处理
            cleaned_cells.append(str(cell))
    return cleaned_cells
