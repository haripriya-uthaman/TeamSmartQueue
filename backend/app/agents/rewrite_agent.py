import logging
from typing import List
from app.services.gemini_service import gemini_service
from app.schemas.ticket import TicketSubmission, ClarificationResponse, RewrittenTicket

logger = logging.getLogger(__name__)


class RewriteAgent:
    """
    RewriteAgent reconstructs a professional, well-formatted software support ticket
    combining the original ticket data and any clarifying answers provided by the user.
    """
    def __init__(self) -> None:
        self.service = gemini_service

    from tenacity import retry, wait_exponential, stop_after_attempt

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def rewrite_ticket(self, ticket: TicketSubmission, answers: List[ClarificationResponse]) -> RewrittenTicket:
        """
        Rewrites a support ticket by combining original info and user clarification responses.
        
        Args:
            ticket (TicketSubmission): The original ticket submission.
            answers (List[ClarificationResponse]): The answers provided by the user.
            
        Returns:
            RewrittenTicket: The rewritten, professionally formatted ticket structure.
        """
        logger.info("Rewriting ticket: '%s'", ticket.title)
        
        answers_str = ""
        if answers:
            answers_str = "\n".join(
                f"- Answer for question ID '{ans.question_id}': {ans.answer_text}" 
                for ans in answers
            )
        else:
            answers_str = "No clarification answers provided by the user."
            
        prompt = f"""
You are a professional technical writer and software support coordinator.
Your task is to take the following original ticket and the user's answers to clarifying questions, and rewrite them into a clean, structured, professional bug report/ticket.

Original Ticket Title: {ticket.title}
Original Ticket Description: {ticket.description}

Clarification Answers:
{answers_str}

Evaluate the data and rewrite the ticket.
The rewritten ticket should have a highly professional tone and be formatted with the following clear elements:
1. Title: A concise, descriptive, and professional bug title (e.g., prefix with component tags if applicable).
2. Description: A structured explanation of the problem.
3. Environment: OS, browser version, platform, or other runtime details.
4. Steps to Reproduce: Step-by-step description of how to reproduce the bug.
5. Expected Result: What should have happened.
6. Actual Result: What actually happened.

RULES:
- NEVER hallucinate or invent facts. Do not make up OS names, browser names, versions, or error logs.
- If information for a section (e.g., Environment, Steps to Reproduce, Expected/Actual Results) is NOT available in either the original ticket or the user's answers, write "UNKNOWN" for that section.
- Compile observations cleanly.

Output must conform to the `RewrittenTicket` schema.
"""

        try:
            rewritten_result = self.service.generate_structured(
                prompt=prompt,
                schema=RewrittenTicket,
                temperature=0.2,
            )
            logger.info("Successfully completed ticket rewrite. Title: '%s'", rewritten_result.rewritten_title)
            return rewritten_result
            
        except Exception as e:
            logger.error("Error occurred in RewriteAgent: %s", str(e), exc_info=True)
            raise e
