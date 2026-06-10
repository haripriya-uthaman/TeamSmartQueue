import logging
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception
from app.core.config import settings

logger = logging.getLogger(__name__)


def should_retry_github_error(exception: Exception) -> bool:
    """
    Checks if a GitHub exception is transient (network timeout, rate limit, or 5xx server error).
    Do NOT retry on permanent client errors like 400, 401, 403, or 404.
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on rate limit (429) or server errors (5xx)
        return status_code == 429 or status_code >= 500
    if isinstance(exception, httpx.RequestError):
        # Retry on network failures (connection refused, timeout, DNS resolution failure)
        return True
    return False


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

    def validate_credentials(self) -> dict:
        """
        Validates the configured GitHub token and repository permissions.
        Returns a dict indicating verification status and details.
        """
        if not self.token or not self.owner or not self.repo:
            return {
                "valid": False,
                "reason": "Missing GitHub credentials (token, owner, or repo) in configuration."
            }

        url = f"{self.base_url}/repos/{self.owner}/{self.repo}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-API-Version": "2022-11-28",
            "User-Agent": "FastAPI-AI-Ticket-Quality-Auditor"
        }

        logger.info("Validating GitHub PAT permissions for repository: %s/%s", self.owner, self.repo)
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 401:
                    return {"valid": False, "reason": "Unauthorized: Invalid GitHub Token."}
                elif response.status_code == 403:
                    return {"valid": False, "reason": "Forbidden: Token lacks access to this repository."}
                elif response.status_code == 404:
                    return {"valid": False, "reason": "Not Found: Repository does not exist or is private."}
                
                response.raise_for_status()
                data = response.json()
                
                permissions = data.get("permissions", {})
                has_write = permissions.get("push", False) or permissions.get("admin", False)
                
                if not has_write:
                    return {
                        "valid": False,
                        "reason": f"Forbidden: Token has read access but lacks write (push) access to {self.owner}/{self.repo}."
                    }
                
                return {
                    "valid": True,
                    "permissions": permissions,
                    "message": f"Successfully authenticated. Token has write access to {self.owner}/{self.repo}."
                }
        except Exception as e:
            logger.error("Error validating GitHub PAT credentials: %s", str(e), exc_info=True)
            return {
                "valid": False,
                "reason": f"Network or unexpected error validating GitHub PAT: {str(e)}"
            }

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(should_retry_github_error),
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
                raise e
            except Exception as e:
                logger.error("Unexpected error calling GitHub API: %s", str(e), exc_info=True)
                raise e
