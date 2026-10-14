import pytest

from solace.assistant_router import route_request


@pytest.mark.parametrize(
    ("user_text", "command"),
    [
        ("fix the grammar: i has notes", "grammar"),
        ("find the file named report.pdf", "file"),
        ("inspect my website project", "do"),
        ("make an Excel formula for totals", "excel"),
        ("explain Bash pipes", "ask"),
        ("search my journal memories for Lagos", "search"),
    ],
)
def test_routes_known_work_to_deterministic_skills(user_text, command):
    route = route_request(user_text)
    assert route.kind == "deterministic"
    assert route.command == command


def test_unknown_request_requires_local_model():
    route = route_request("compare the themes in two fantasy novels")
    assert route.kind == "local_model"
    assert route.command is None


def test_empty_request_is_rejected():
    with pytest.raises(ValueError):
        route_request("  ")
