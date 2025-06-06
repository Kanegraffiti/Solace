#!/usr/bin/env python3
"""Import code examples from a plain text file into Solace knowledge."""
from __future__ import annotations
import re
from pathlib import Path
import argparse

from solace.logic.codegen import add_example


def parse_examples(text: str, language: str) -> list[dict]:
    examples = []
    pattern = re.compile(r"```{}\n(.*?)\n```".format(re.escape(language)), re.DOTALL)
    for match in pattern.finditer(text):
        code = match.group(1).strip()
        before = text[:match.start()].splitlines()
        desc = before[-1].strip() if before else f"Example for {language}"
        examples.append({'description': desc, 'code': code, 'explanation': desc})
    return examples


def main() -> None:
    ap = argparse.ArgumentParser(description='Import open book examples')
    ap.add_argument('file', help='text file with code blocks')
    ap.add_argument('language', help='language of code blocks')
    args = ap.parse_args()

    path = Path(args.file)
    text = path.read_text(encoding='utf-8')
    exs = parse_examples(text, args.language)
    for ex in exs:
        add_example(args.language, ex['description'], ex['code'], ex['explanation'])
    print(f'Imported {len(exs)} examples.')


if __name__ == '__main__':
    main()
