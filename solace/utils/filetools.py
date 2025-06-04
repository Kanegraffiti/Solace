from pathlib import Path
import json
import pdfplumber
from ebooklib import epub
from bs4 import BeautifulSoup
import markdown
from docutils.core import publish_string


def read_text(path: Path) -> str:
    if path.suffix == '.txt':
        return path.read_text(encoding='utf-8')
    elif path.suffix == '.md':
        html = markdown.markdown(path.read_text(encoding='utf-8'))
        return BeautifulSoup(html, 'html.parser').get_text()
    elif path.suffix == '.rst':
        html = publish_string(path.read_text(encoding='utf-8'), writer_name='html')
        return BeautifulSoup(html, 'html.parser').get_text()
    elif path.suffix == '.pdf':
        text = ''
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + '\n'
        return text
    elif path.suffix == '.epub':
        book = epub.read_epub(str(path))
        text = ''
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text += soup.get_text() + '\n'
        return text
    else:
        raise ValueError('Unsupported file type')


def load_imported(path: str):
    p = Path(path)
    content = read_text(p)
    return [{'text': line.strip()} for line in content.splitlines() if line.strip()]
