import pytest

from solace.logic.converse import ConversationState, get_reply, offline_reply


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("hello", "Hello, Ada"),
        ("I feel sad about losing the opportunity", "painful"),
        ("I am overwhelmed with tomorrow's meeting", "most urgent"),
        ("I am frustrated about this broken script", "next practical move"),
        ("I am proud of the website", "matters most"),
        ("I finished the client project", "You did it"),
        ("Thank you for helping", "You're welcome"),
        ("Should I take the bus or the car?", "time, money, risk, or energy"),
        ("I need to prepare the presentation", "workable next step"),
        ("What is today's weather?", "live information"),
        ("Who invented quantum frobnication?", "don't know that reliably"),
        ("My client changed the brief again", "client changed the brief"),
    ],
)
def test_conversation_intents_are_specific(message, expected):
    reply = offline_reply(message, name="Ada")
    assert expected.lower() in reply.lower()


def test_short_follow_up_uses_session_topic():
    state = ConversationState()
    offline_reply("I am anxious about the hospital interview", state=state)

    reply = offline_reply("I don't know", state=state)

    assert "hospital interview" in reply
    assert "first detail" in reply


@pytest.mark.parametrize(
    ("follow_up", "expected"),
    [
        ("yes", "focus on first"),
        ("no", "more useful"),
        ("maybe", "holding you back"),
        ("okay", "whenever you're ready"),
    ],
)
def test_brief_replies_continue_the_current_subject(follow_up, expected):
    state = ConversationState(last_topic="the deployment")
    reply = offline_reply(follow_up, state=state)
    assert "deployment" in reply
    assert expected in reply


def test_repeated_input_does_not_repeat_the_same_reply():
    state = ConversationState()
    first = offline_reply("The client changed the deadline", state=state)
    second = offline_reply("The client changed the deadline", state=state)

    assert first != second
    assert "client changed the deadline" in second


def test_tone_setting_changes_response_length():
    quiet = offline_reply("I am sad about the result", tone="quiet")
    verbose = offline_reply("I am sad about the result", tone="verbose")

    assert len(verbose) > len(quiet)
    assert "one piece at a time" in verbose


def test_crisis_language_prioritises_immediate_human_support():
    reply = offline_reply("I want to kill myself")
    assert "emergency services" in reply
    assert "trusted person" in reply


@pytest.mark.parametrize(
    ("question", "invented_fact"),
    [
        ("Where do you live?", "near the river"),
        ("What is your name?", "John"),
        ("How old are you?", "thirty"),
        ("What is the weather like?", "sunny and warm"),
    ],
)
def test_backward_compatible_reply_does_not_invent_a_biography(question, invented_fact):
    reply = get_reply(question)
    assert invented_fact.lower() not in reply.lower()


def test_state_is_session_only_and_explicit():
    first_state = ConversationState()
    second_state = ConversationState()
    offline_reply("I am worried about my interview", state=first_state)

    assert first_state.last_topic == "my interview"
    assert second_state.last_topic == ""
