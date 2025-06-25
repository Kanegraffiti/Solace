import re
from typing import Dict, List

DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
LOCATION_PATTERN = re.compile(r"\b(?:in|at|from)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*)")
NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+\s[A-Z][a-z]+)\b")


def extract_dates(text: str) -> List[str]:
    return DATE_PATTERN.findall(text)


def extract_locations(text: str) -> List[str]:
    return LOCATION_PATTERN.findall(text)


def extract_names(text: str) -> List[str]:
    return NAME_PATTERN.findall(text)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Return a dict of extracted entity lists."""
    return {
        "dates": extract_dates(text),
        "locations": extract_locations(text),
        "names": extract_names(text),
    }

