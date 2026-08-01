from services.memory.embeddings import EMBEDDING_DIMENSION, embed_text
from services.orchestrator.capabilities import plan_actions_for_goal


def test_embed_text_is_deterministic_and_fixed_size() -> None:
    first = embed_text("Local AI Agent")
    second = embed_text("Local AI Agent")
    assert first == second
    assert len(first) == EMBEDDING_DIMENSION
    assert embed_text("   ") == [0.0] * EMBEDDING_DIMENSION


def test_plan_actions_for_goal_detects_web_and_default() -> None:
    web_actions = plan_actions_for_goal("Please fetch https://example.com/docs")
    assert any(action.name == "web_fetch" for action in web_actions)

    default_actions = plan_actions_for_goal("say hello")
    assert default_actions
    assert default_actions[0].name == "reflect"
