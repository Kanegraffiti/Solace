from ..utils.storage import load_facts


def answer_question(question: str) -> str:
    facts = load_facts().get('facts', {})
    question_lower = question.lower()
    for key, value in facts.items():
        if key.lower() in question_lower:
            return value
    return "I don't know the answer to that."
