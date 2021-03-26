from patient_abm.agent.base import Agent
from patient_abm.utils import string_to_datetime


def test_agent():
    agent_id = 12345
    created_at = "2021-03-09"
    agent = Agent(id_=agent_id, created_at=created_at)

    assert agent.id == agent_id
    assert agent.created_at == string_to_datetime(created_at)
    assert (
        agent.__repr__()
        == f"Agent(id={agent_id}, created_at={string_to_datetime(created_at)})"
    )
