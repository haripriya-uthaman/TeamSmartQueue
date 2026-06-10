import logging
from app.services.gemini_service import gemini_service
from app.schemas.ticket import TicketSubmission, AuditResult

logger = logging.getLogger(__name__)


class AuditAgent:
    """
    AuditAgent evaluates a support ticket's quality, assigns a score,
    and identifies missing details using Gemini structure validation.
    """
    def __init__(self) -> None:
        self.gemini_client = gemini_service

    # pyrefly: ignore [missing-import]
    from tenacity import retry, wait_exponential, stop_after_attempt
    # pyrefly: ignore [missing-import]
    from google.genai.errors import APIError

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def audit_ticket(self, ticket: TicketSubmission) -> AuditResult:
        """
        Audits the provided ticket submission by sending it to the Gemini model.
        It analyzes the text based on 6 core quality metrics (Title, Description, Environment,
        Steps, Expected Result, and Actual Result) and flags missing information.
        
        Args:
            ticket (TicketSubmission): The ticket data to evaluate.
            
        Returns:
            AuditResult: The structured results of the audit.
        """
        logger.info("AuditAgent: Starting quality audit workflow for ticket: '%s'", ticket.title)
        
        # Strip inputs to remove any accidental leading or trailing whitespace
        clean_title = ticket.title.strip()
        clean_description = ticket.description.strip()
        
        prompt = f"""
You are an expert software quality auditor and technical support reviewer.
Your task is to analyze the quality of the following submitted support ticket.
 
Ticket Title: {clean_title}
Ticket Description: {clean_description}
 
Analyze the ticket based on the presence, clarity, and precision of these 6 key sections:
1. Title: Is the title clear, concise, and descriptive of the actual issue?
2. Description: Is the detailed explanation clear and easy to follow?
3. Environment: Does it mention OS, browser, application version, or relevant hardware/platform?
4. Steps to Reproduce: Are there clear, step-by-step instructions to trigger the bug?
5. Expected Result: Does it specify what should have happened?
6. Actual Result: Does it specify what actually happened?

RULES:
- Evaluate only the information explicitly provided in the ticket. Never invent, assume, or guess details.
- If any of the above 6 critical sections are missing or unclear, they MUST be listed in the `missing_information` array.
- In `findings`, outline what sections are present, what is missing, and general observations.
- Assign a quality `score` between 0.0 and 100.0 based on how complete and clear the ticket is. A perfect ticket has all 6 sections clearly detailed.
- If there is any missing or unclear critical information, set `requires_clarification` to true. Otherwise, set it to false.
"""

        try:
            audit_result = self.gemini_client.generate_structured(
                prompt=prompt,
                schema=AuditResult,
                temperature=0.1,
            )
            logger.info("Successfully completed ticket audit. Score: %.1f", audit_result.score)
            return audit_result
            
        except Exception as e:
            logger.error("Error occurred in AuditAgent: %s", str(e), exc_info=True)
            raise e
