import logging
from app.services.ai_service import ai_service as gemini_service
from app.schemas.ticket import TicketSubmission, AuditResult

logger = logging.getLogger(__name__)


class AuditAgent:
    """
    AuditAgent evaluates a support ticket's quality, assigns a score,
    and identifies missing details using Gemini structure validation.
    """
    def __init__(self) -> None:
        self.service = gemini_service

    from tenacity import retry, wait_exponential, stop_after_attempt
    from google.genai.errors import APIError

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def audit_ticket(self, ticket: TicketSubmission, ocr_text: str = "") -> AuditResult:
        """
        Audits the provided ticket submission, optionally enriched with OCR text from attachments.
        """
        logger.info("Auditing ticket: '%s'", ticket.title)

        steps_str = ""
        if ticket.steps_to_reproduce:
            steps_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(ticket.steps_to_reproduce))

        ocr_section = ""
        if ocr_text:
            ocr_section = f"\nAttachment OCR / Screenshot Analysis:\n{ocr_text}\n"

        prompt = f"""
You are an expert software quality auditor and technical support reviewer.
Your task is to analyze the quality of the following submitted support ticket.

Ticket Title: {ticket.title}
Ticket Description: {ticket.description}
Environment: {ticket.environment or 'NOT PROVIDED'}
Steps to Reproduce:
{steps_str if steps_str else 'NOT PROVIDED'}
Expected Result: {ticket.expected_result or 'NOT PROVIDED'}
Actual Result: {ticket.actual_result or 'NOT PROVIDED'}
Priority: {ticket.priority or 'NOT PROVIDED'}
Severity: {ticket.severity or 'NOT PROVIDED'}
{ocr_section}
Analyze the ticket based on the presence, clarity, and precision of these 6 key sections:
1. Title: Is the title clear, concise, and descriptive of the actual issue?
2. Description: Is the detailed explanation clear and easy to follow?
3. Environment: Does it mention OS, browser, application version, or relevant hardware/platform?
4. Steps to Reproduce: Are there clear, step-by-step instructions to trigger the bug?
5. Expected Result: Does it specify what should have happened?
6. Actual Result: Does it specify what actually happened?

RULES:
- Evaluate only the information explicitly provided in the ticket AND in the attachment OCR (if any).
- If any of the above 6 critical sections are missing or unclear, they MUST be listed in the `missing_information` array.
- If attachment OCR fills in missing information, credit it accordingly in the score.
- In `findings`, outline what sections are present, what is missing, and general observations.
- Assign a quality `score` between 0.0 and 100.0 based on how complete and clear the ticket is.
- If there is any missing or unclear critical information, set `requires_clarification` to true. Otherwise, set it to false.
"""

        try:
            audit_result = self.service.generate_structured(
                prompt=prompt,
                schema=AuditResult,
                temperature=0.1,
            )
            logger.info("Successfully completed ticket audit. Score: %.1f", audit_result.score)
            return audit_result
            
        except Exception as e:
            logger.error("Error occurred in AuditAgent: %s", str(e), exc_info=True)
            raise e
