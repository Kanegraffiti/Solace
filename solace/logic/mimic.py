import random
from collections import Counter
from nltk import word_tokenize, bigrams

from ..utils.storage import load_entries


def build_profile():
    entries = load_entries()
    tokens = []
    for e in entries:
        tokens.extend(word_tokenize(e['text'].lower()))
    bi = list(bigrams(tokens))
    counts = Counter(bi)
    common = [' '.join(b) for b, _ in counts.most_common(50)]
    return common


def mimic_reply(prompt: str) -> str:
    phrases = build_profile()
    if not phrases:
        return "I'm still learning from you."
    choice = random.choice(phrases)
    return f"{choice.capitalize()} ..."
