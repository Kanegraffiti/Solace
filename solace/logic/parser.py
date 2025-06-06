from pathlib import Path
from ..utils.filehandler import read_text


def _load_imported(path: Path):
    content = read_text(path)
    return [{'text': line.strip()} for line in content.splitlines() if line.strip()]


def parse_file(path: str):
    return _load_imported(Path(path))
