from __future__ import annotations

from pathlib import Path

try:
    import pdfplumber  # type: ignore
except Exception:  # noqa: PIE786
    pdfplumber = None

try:
    from ebooklib import epub  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # noqa: PIE786
    epub = None
    BeautifulSoup = None

try:
    import markdown  # type: ignore
except Exception:  # noqa: PIE786
    markdown = None

try:
    from docutils.core import publish_string  # type: ignore
except Exception:  # noqa: PIE786
    publish_string = None


SUPPORTED_SUFFIXES = {'.txt', '.md', '.rst', '.pdf', '.epub', '.py'}


def is_supported(path: Path) -> bool:
    """Return True if the file extension is supported."""
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def read_text(path: Path) -> str:
    """Read text from the supported ``path``."""
    suf = path.suffix.lower()
    if suf == '.txt':
        return path.read_text(encoding='utf-8')
    if suf == '.py':
        return path.read_text(encoding='utf-8')
    if suf == '.md':
        if markdown is None:
            raise RuntimeError('markdown package required for .md files')
        html = markdown.markdown(path.read_text(encoding='utf-8'))
        if BeautifulSoup is None:
            return html
        return BeautifulSoup(html, 'html.parser').get_text()
    if suf == '.rst':
        if publish_string is None:
            raise RuntimeError('docutils required for .rst files')
        html = publish_string(path.read_text(encoding='utf-8'), writer_name='html')
        if BeautifulSoup is None:
            return html.decode('utf-8') if isinstance(html, bytes) else html
        raw = html.decode('utf-8') if isinstance(html, bytes) else html
        return BeautifulSoup(raw, 'html.parser').get_text()
    if suf == '.pdf':
        if pdfplumber is None:
            raise RuntimeError('pdfplumber required for .pdf files')
        text = ''
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                text += page_text + '\n'
        return text
    if suf == '.epub':
        if epub is None or BeautifulSoup is None:
            raise RuntimeError('ebooklib and beautifulsoup4 required for .epub files')
        book = epub.read_epub(str(path))
        text = ''
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text += soup.get_text() + '\n'
        return text
    raise ValueError('Unsupported file type: ' + path.suffix)
