from ..utils.filetools import load_imported


def parse_file(path: str):
    return load_imported(path)
