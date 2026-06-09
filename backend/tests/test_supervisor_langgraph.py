from app.agents.supervisor_agent import SupervisorAgent
from app.schemas.ticket import (
    AuditResult,
    ClarificationQuestion,
    DuplicateResult,
    RewrittenTicket,
    TicketSubmission,
)


class FakeAuditAgent:
    def __init__(self, audit_result):
        self.audit_result = audit_result

    def audit_ticket(self, ticket):
        return self.audit_result


class FakeQuestionAgent:
    def generate_questions(self, ticket, audit):
        return [
            ClarificationQuestion(
                question_id="q1",
                field_or_topic="environment",
                question_text="Which OS and browser did you use?",
            )
        ]


class FakeRewriteAgent:
    def rewrite_ticket(self, ticket, answers):
        return RewrittenTicket(
            rewritten_title="[Checkout] Submit button fails",
            rewritten_description=(
                "## Description\nSubmit button fails.\n\n"
                "## Environment\nUNKNOWN\n\n"
                "## Steps to Reproduce\nUNKNOWN\n\n"
                "## Expected Result\nUNKNOWN\n\n"
                "## Actual Result\nUNKNOWN"
            ),
            improvements_made=["Structured the report without inventing missing details."],
        )


class FakeDuplicateService:
    def __init__(self, result):
        self.result = result
        self.indexed = []

    def find_duplicate(self, title, description, threshold=0.85):
        return self.result

    def add_ticket(self, ticket_id, title, description, metadata=None):
        self.indexed.append(
            {
                "ticket_id": ticket_id,
                "title": title,
                "description": description,
                "metadata": metadata or {},
            }
        )


class FakeGitHubService:
    def create_issue(self, title, body):
        return {
            "id": 12345,
            "number": 7,
            "html_url": "https://github.com/example/repo/issues/7",
        }


def make_supervisor(audit_result, duplicate_result):
    supervisor = SupervisorAgent()
    supervisor.audit_agent = FakeAuditAgent(audit_result)
    supervisor.question_agent = FakeQuestionAgent()
    supervisor.rewrite_agent = FakeRewriteAgent()
    supervisor.duplicate_service = FakeDuplicateService(duplicate_result)
    supervisor.github_service = FakeGitHubService()
    supervisor._graph = supervisor._build_graph()
    return supervisor


def test_langgraph_routes_to_clarification_questions():
    supervisor = make_supervisor(
        AuditResult(
            score=40,
            passed=False,
            findings=["Environment is missing."],
            missing_information=["environment"],
            requires_clarification=True,
        ),
        DuplicateResult(is_duplicate=False),
    )

    response = supervisor.run_workflow(
        TicketSubmission(title="Checkout broken", description="Submit does not work."),
        thread_id="test:clarification",
    )

    assert response.status == "needs_clarification"
    assert response.questions
    assert response.questions[0].field_or_topic == "environment"


def test_langgraph_completes_and_indexes_non_duplicate_ticket():
    supervisor = make_supervisor(
        AuditResult(
            score=95,
            passed=True,
            findings=["All required details are present."],
            missing_information=[],
            requires_clarification=False,
        ),
        DuplicateResult(is_duplicate=False, similarity_score=0.2),
    )

    response = supervisor.run_workflow(
        TicketSubmission(title="Checkout submit button fails", description="Complete bug report."),
        thread_id="test:completed",
    )

    assert response.status == "completed"
    assert response.github_issue_number == 7
    assert response.rewritten_ticket.rewritten_title == "[Checkout] Submit button fails"
    assert supervisor.duplicate_service.indexed[0]["ticket_id"] == "12345"


def test_langgraph_stops_before_github_for_duplicate_ticket():
    supervisor = make_supervisor(
        AuditResult(
            score=90,
            passed=True,
            findings=["Ticket is clear."],
            missing_information=[],
            requires_clarification=False,
        ),
        DuplicateResult(
            is_duplicate=True,
            duplicate_ticket_id="existing-1",
            similarity_score=0.94,
            matching_explanation="Nearest ticket is above threshold.",
        ),
    )

    response = supervisor.run_workflow(
        TicketSubmission(title="Checkout submit button fails", description="Complete bug report."),
        thread_id="test:duplicate",
    )


    assert response.duplicate_result.duplicate_ticket_id == "existing-1"
    assert supervisor.duplicate_service.indexed == []
