"""Document parsers for various file formats."""

from .markdown import MarkdownParser
from .text import TextParser
from .json_parser import JsonParser
from .html import HtmlParser
from .pdf import PdfParser
from .docx import DocxParser

PARSERS = {
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".txt": TextParser,
    ".text": TextParser,
    ".log": TextParser,
    ".csv": TextParser,
    ".json": JsonParser,
    ".html": HtmlParser,
    ".htm": HtmlParser,
    ".pdf": PdfParser,
    ".docx": DocxParser,
}

__all__ = ["PARSERS", "MarkdownParser", "TextParser", "JsonParser", "HtmlParser", "PdfParser", "DocxParser"]
