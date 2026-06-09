import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """
    GitHubService handles communication with the GitHub REST API to manage issues
    in the configured repository.
    """
    def __init__(self) -> None:
        self.token = settings.GITHUB_TOKEN
        self.owner = settings.GITHUB_OWNER
        self.repo = settings.GITHUB_REPO
        self.base_url = "https://api.github.com"

    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
    import httpx

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, Exception)),
        reraise=True
    )
    def create_issue(self, title: str, body: str) -> dict:
        """
        Creates a new GitHub issue in the repository.
        
        Args:
            title (str): The issue title.
            body (str): The description or body of the issue in Markdown.
            
        Returns:
            dict: The JSON response parsed from the GitHub API.
        """
        if not self.token or not self.owner or not self.repo:
            logger.error("GitHub integration credentials are not fully configured in environment settings.")
            raise ValueError("GitHub credentials (token, owner, repo) are not configured in settings.")

        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-API-Version": "2022-11-28",
            "User-Agent": "FastAPI-AI-Ticket-Quality-Auditor"
        }
        payload = {
            "title": title,
            "body": body
        }

        logger.info("Creating GitHub Issue in repo: %s/%s", self.owner, self.repo)
        
        with httpx.Client(timeout=15.0) as client:
            try:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info("Successfully created GitHub issue #%d: %s", data.get("number"), data.get("html_url"))
                return data
            except httpx.HTTPStatusError as e:
                logger.error("GitHub API HTTP Error: %s - Response: %s", str(e), response.text)
                raise ValueError(f"GitHub API returned error: {response.status_code} - {response.text}") from e
            except Exception as e:
                logger.error("Unexpected error calling GitHub API: %s", str(e), exc_info=True)
                raise e
