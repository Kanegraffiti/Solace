MOOD_KEYWORDS = {
    'happy': ['happy', 'glad', 'joy', 'excited', 'great'],
    'sad': ['sad', 'down', 'unhappy', 'depressed', 'bad'],
    'angry': ['angry', 'mad', 'furious', 'annoyed'],
    'anxious': ['worried', 'anxious', 'nervous', 'scared'],
}

def detect_mood(text: str) -> str:
    lower = text.lower()
    for mood, words in MOOD_KEYWORDS.items():
        for w in words:
            if w in lower:
                return mood
    return 'neutral'
