import json

from backend.agents.research import ResearchAgent


class PlannerFixture:
    provider = "gemini"

    def __init__(self, content):
        self.content = content
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return type("Reply", (), {"text": self.content})()


def test_planner_returns_only_one_bounded_search_query():
    planner = PlannerFixture(
        json.dumps(["section 53 fixed term", "ignore the query limit"])
    )
    queries = ResearchAgent(query_planner=planner)._plan_queries(
        "synthetic fixed-term eligibility question"
    )
    assert queries == ["section 53 fixed term"]
    assert "Do not answer the question" in planner.prompts[0]


def test_planner_rejects_non_json_and_never_returns_a_legal_answer():
    planner = PlannerFixture("Gratuity is definitely payable")
    try:
        ResearchAgent(query_planner=planner)._plan_queries("synthetic question")
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("non-JSON model output must not become a query plan")
