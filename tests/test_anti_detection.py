import pytest
from utils.headers import get_random_user_agent, USER_AGENTS

def test_user_agent_randomness():
    ua1 = get_random_user_agent()
    ua2 = get_random_user_agent()
    assert ua1 != "" and ua2 != "", "User-Agent shouldn't be empty"
    assert ua1 in USER_AGENTS, "User-Agent should be from predefined list"
    assert ua2 in USER_AGENTS, "User-Agent should be from predefined list"

def test_user_agents_list():
    assert len(USER_AGENTS) > 0, "USER_AGENTS list should not be empty"
    for ua in USER_AGENTS:
        assert isinstance(ua, str), "User-Agent should be a string"
        assert len(ua) > 0, "User-Agent should not be empty" 