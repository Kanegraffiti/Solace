import json
from collections import Counter
from pathlib import Path

import pytest

from solace.logic import bash_intel

CASES_PATH = Path(__file__).parent / "data" / "bash_fluency_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _case_id(case):
    return case["id"]


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_bash_fluency_case(case):
    category = case["category"]
    prompt = case["input"]
    expected = case["expected"]

    if category == "routing":
        assert bash_intel.is_bash_query(prompt) is expected
        return

    if category == "lookup":
        result = bash_intel.lookup_bash(prompt)
        assert result is not None, "Solace returned no Bash task match"
        actual = result.command
    elif category == "explain":
        actual = "\n".join(bash_intel.explain_command(prompt))
    elif category == "debug":
        actual = bash_intel.debug_bash_error(prompt) or ""
    elif category == "safety":
        actual = "\n".join(bash_intel.classify_safety(prompt))
    else:
        pytest.fail(f"Unknown benchmark category: {category}")

    for fragment in expected:
        assert fragment.lower() in actual.lower(), (
            f"Expected {fragment!r} in {category} output for {prompt!r}; got {actual!r}"
        )


def test_bash_fluency_dataset_shape():
    assert len(CASES) == 50
    assert len({case["id"] for case in CASES}) == len(CASES)
    counts = Counter(case["category"] for case in CASES)
    assert counts == {
        "routing": 10,
        "lookup": 18,
        "explain": 10,
        "debug": 6,
        "safety": 6,
    }
