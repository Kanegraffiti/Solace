from ..utils.storage import load_facts, save_facts


def add_fact(key: str, value: str):
    data = load_facts()
    facts = data.get('facts', {})
    facts[key] = value
    data['facts'] = facts
    save_facts(data)


def add_snippet(key: str, code: str):
    data = load_facts()
    snips = data.get('snippets', {})
    snips[key] = code
    data['snippets'] = snips
    save_facts(data)
