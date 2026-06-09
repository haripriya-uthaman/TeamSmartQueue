from app.agents.question_agent import QuestionAgent, QuestionListWrapper
from app.schemas.ticket import AuditResult, ClarificationQuestion, TicketSubmission


class FakeQuestionService:
    def generate_structured(self, prompt, schema, temperature=0.3):
        assert schema is QuestionListWrapper
        return QuestionListWrapper(
            questions=[
                ClarificationQuestion(
                    question_id=f"q{i}",
                    field_or_topic="missing_detail",
                    question_text=f"Question {i}?",
                )
                for i in range(1, 5)
            ]
        )


def test_question_agent_never_returns_more_than_three_questions():
    agent = QuestionAgent()
    agent.service = FakeQuestionService()

    questions = agent.generate_questions(
        TicketSubmission(title="Broken checkout", description="The checkout button is broken."),
        AuditResult(
            score=20,
            passed=False,
            findings=["Key debugging details are missing."],
            missing_information=["environment", "steps", "expected", "actual"],
            requires_clarification=True,
        ),
    )

    assert len(questions) == 3
    assert [question.question_id for question in questions] == ["q1", "q2", "q3"]
