import json
import sys
from .utils.storage import load_facts, save_facts


def load_file(path):
    data = json.load(open(path))
    facts = load_facts()
    facts.update(data)
    save_facts(facts)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python teach_loader.py <json_file>')
        sys.exit(1)
    load_file(sys.argv[1])
    print('Facts loaded')
