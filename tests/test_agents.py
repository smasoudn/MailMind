import os
import pytest
from unittest.mock import patch

# Set dummy API key before importing agents
os.environ["OPENAI_API_KEY"] = "dummy"

from agents import (
    routing_agent,
    input_parser,
    intent_detector,
    personalization_agent,
    draft_writer,
    tone_stylist,
    review_validator,
    RoutingDecision,
    ParsedInput,
    IntentOutput,
    ValidationResult
)

class MockModerationResult:
    def __init__(self, flagged):
        self.flagged = flagged

class MockModerationCreate:
    def __init__(self, flagged):
        self.results = [MockModerationResult(flagged)]

class MockModerationEndpoint:
    def __init__(self, flagged):
        self._flagged = flagged
    def create(self, input):
        return MockModerationCreate(self._flagged)

class MockOpenAIClient:
    def __init__(self, flagged=False):
        self.moderations = MockModerationEndpoint(flagged)

@pytest.fixture
def clean_openai_client(mocker):
    return mocker.patch('agents.OpenAI', return_value=MockOpenAIClient(flagged=False))

@pytest.fixture
def flagged_openai_client(mocker):
    return mocker.patch('agents.OpenAI', return_value=MockOpenAIClient(flagged=True))

@pytest.fixture
def mock_chain_invoke(mocker):
    return mocker.patch('langchain_core.runnables.RunnableSequence.invoke')

# --- Agent Tests ---

def test_routing_agent_moderation_flagged(flagged_openai_client):
    state = {"raw_prompt": "bad prompt"}
    res = routing_agent(state)
    assert res["routing_decision"] == "reject"
    assert "violates" in res["error"]

def test_routing_agent_valid(clean_openai_client, mock_chain_invoke):
    mock_chain_invoke.return_value = RoutingDecision(is_valid=True, reason="")
    state = {"raw_prompt": "good prompt"}
    res = routing_agent(state)
    assert res["routing_decision"] == "continue"
    assert res["error"] is None

def test_routing_agent_invalid_prompt(clean_openai_client, mock_chain_invoke):
    mock_chain_invoke.return_value = RoutingDecision(is_valid=False, reason="Not an email")
    state = {"raw_prompt": "what is 2+2"}
    res = routing_agent(state)
    assert res["routing_decision"] == "reject"
    assert res["error"] == "Not an email"

def test_input_parser(mock_chain_invoke):
    mock_chain_invoke.return_value = ParsedInput(key_points=["point1"], urgency="high")
    res = input_parser({"raw_prompt": "test"})
    assert "parsed_input" in res
    assert res["parsed_input"]["key_points"] == ["point1"]

def test_intent_detector(mock_chain_invoke):
    mock_chain_invoke.return_value = IntentOutput(intent="Request")
    res = intent_detector({"raw_prompt": "test"})
    assert res["intent"] == "Request"

def test_personalization_agent(mocker):
    mocker.patch('builtins.open', side_effect=FileNotFoundError)
    state = {"sender_id": "user_1", "recipient_type": "colleague"}
    res = personalization_agent(state)
    assert "personalized_context" in res
    assert res["personalized_context"]["sender_name"] == "User"

def test_draft_writer(mock_chain_invoke):
    mock_chain_invoke.return_value = "Draft output"
    state = {
        "intent": "Update",
        "parsed_input": {"key_points": ["done"]},
        "personalized_context": {"recipient_guidance": ""}
    }
    res = draft_writer(state)
    assert res["draft"] == "Draft output"

def test_tone_stylist(mock_chain_invoke):
    mock_chain_invoke.return_value = "Styled output"
    state = {
        "tone": "Professional",
        "draft": "Draft output",
        "personalized_context": {"sender_style": "", "sender_sign_off": "Best"}
    }
    res = tone_stylist(state)
    assert res["tone_styled_draft"] == "Styled output"

def test_review_validator_moderation_flagged(flagged_openai_client):
    state = {"tone_styled_draft": "bad draft", "retry_count": 0}
    res = review_validator(state)
    assert "validation_feedback" in res
    assert "violated" in res["validation_feedback"]
    assert res["retry_count"] == 1

def test_review_validator_moderation_flagged_max_retries(flagged_openai_client):
    state = {"tone_styled_draft": "bad draft", "retry_count": 2}
    res = review_validator(state)
    assert "final_email" in res
    assert "Max retries" in res["validation_feedback"]

def test_review_validator_invalid_llm(clean_openai_client, mock_chain_invoke):
    mock_chain_invoke.return_value = ValidationResult(is_valid=False, feedback="Grammar error")
    state = {
        "tone_styled_draft": "good draft",
        "retry_count": 0,
        "tone": "Professional",
        "intent": "Update",
        "parsed_input": {"key_points": []}
    }
    res = review_validator(state)
    assert res["validation_feedback"] == "Grammar error"
    assert res["retry_count"] == 1

def test_review_validator_valid_llm(clean_openai_client, mock_chain_invoke):
    mock_chain_invoke.return_value = ValidationResult(is_valid=True, feedback="")
    state = {
        "tone_styled_draft": "good draft",
        "retry_count": 0,
        "tone": "Professional",
        "intent": "Update",
        "parsed_input": {"key_points": []}
    }
    res = review_validator(state)
    assert "final_email" in res
    assert res["final_email"] == "good draft"
    assert res["validation_feedback"] == "Passed"
