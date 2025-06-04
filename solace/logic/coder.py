from ..utils.storage import load_facts


def generate_code(task: str) -> str:
    facts = load_facts()
    for key, snippet in facts.get('snippets', {}).items():
        if key.lower() in task.lower():
            return snippet
    return '# no snippet found for task'
