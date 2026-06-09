import logging
from typing import List
from pydantic import BaseModel, Field
from app.services.gemini_service import gemini_service
from app.schemas.ticket import TicketSubmission, AuditResult, ClarificationQuestion

logger = logging.getLogger(__name__)


class QuestionListWrapper(BaseModel):
    """
    Wrapper schema to hold a list of clarification questions.
    This guarantees the structure returned by the model matches our expectations.
    """
    questions: List[ClarificationQuestion] = Field(
        ...,
        description="A list of specific, non-redundant clarification questions to ask the user, maximum of 3 items.",
    )


class QuestionAgent:
    """
    QuestionAgent generates highly specific, professional clarification questions
    for the user based on missing information identified in the AuditResult.
    """
    def __init__(self) -> None:
        self.service = gemini_service

    from tenacity import retry, wait_exponential, stop_after_attempt

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def generate_questions(self, ticket: TicketSubmission, audit: AuditResult) -> List[ClarificationQuestion]:
        """
        Generates clarification questions for missing information.
        
        Args:
            ticket (TicketSubmission): The original ticket submission.
            audit (AuditResult): The audit details detailing missing fields.
            
        Returns:
            List[ClarificationQuestion]: Up to 3 structured questions.
        """
        logger.info("Generating clarification questions for ticket: '%s'", ticket.title)
        
        if not audit.missing_information or not audit.requires_clarification:
            logger.info("No missing information or clarification needed. Skipping question generation.")
            return []

        missing_info_str = "\n".join(f"- {info}" for info in audit.missing_information)
        findings_str = "\n".join(f"- {finding}" for finding in audit.findings)
        
        prompt = f"""
You are a helpful customer support and technical QA assistant.
Your goal is to politely gather missing details from the user to help developers debug their issue.

Here is the user's original ticket:
Title: {ticket.title}
Description: {ticket.description}

Here is the audit report of what is missing/unclear:
Score: {audit.score}
Findings:
{findings_str}
Missing Information:
{missing_info_str}

RULES:
- Ask ONLY for the items listed in the "Missing Information" section. Do not ask for anything else.
- Keep the questions specific, clear, polite, and actionable.
- Limit the response to a maximum of 3 questions.
- For each question, output:
  - `question_id`: unique short ID (e.g., "q1", "q2", "q3")
  - `field_or_topic`: the target category (e.g., "environment", "steps_to_reproduce", "expected_result", "actual_result")
  - `question_text`: the polite question text asked to the user
"""

        try:
            wrapper = self.service.generate_structured(
                prompt=prompt,
                schema=QuestionListWrapper,
                temperature=0.3,
            )
            questions = wrapper.questions[:3]
            logger.info("Generated %d clarification questions.", len(questions))
            return questions
            
        except Exception as e:
            logger.error("Error occurred in QuestionAgent: %s", str(e), exc_info=True)
            raise e
