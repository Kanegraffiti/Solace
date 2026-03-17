import re


MOOD_KEYWORDS = {
    'happy': ['happy', 'glad', 'joy', 'excited', 'great', 'grateful', 'hopeful', 'good'],
    'sad': ['sad', 'down', 'unhappy', 'depressed', 'bad', 'lonely', 'tired', 'empty'],
    'angry': ['angry', 'mad', 'furious', 'annoyed', 'irritated', 'frustrated'],
    'anxious': ['worried', 'anxious', 'nervous', 'scared', 'stressed', 'panic'],
}

NEGATIONS = {'not', "don't", "didn't", "isn't", "wasn't", 'never', 'no'}


def _tokenise(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())

def detect_mood(text: str) -> str:
    words = _tokenise(text)
    if not words:
        return 'neutral'

    scores = {mood: 0 for mood in MOOD_KEYWORDS}
    for idx, token in enumerate(words):
        for mood, keywords in MOOD_KEYWORDS.items():
            if token not in keywords:
                continue
            window = words[max(0, idx - 3):idx]
            negated = any(w in NEGATIONS for w in window)
            scores[mood] += -1 if negated else 1

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_mood, top_score = ranked[0]
    if top_score > 0:
        return top_mood
    return 'neutral'
