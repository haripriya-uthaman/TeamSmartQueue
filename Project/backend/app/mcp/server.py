import logging
from mcp.server.fastmcp import FastMCP
from app.services.duplicate_service import duplicate_service
from app.services.github_service import GitHubService

logger = logging.getLogger(__name__)

# Create the FastMCP server instance
mcp = FastMCP("AI Ticket Quality Auditor")


@mcp.tool()
def search_similar_tickets(title: str, description: str, threshold: float = 0.85) -> str:
    """
    Search for similar support tickets in the database using vector embeddings.
    
    Args:
        title (str): Title of the ticket to match.
        description (str): Detailed description of the ticket to match.
        threshold (float): Similarity threshold (0.0 to 1.0) above which a ticket is considered a duplicate.
        
    Returns:
        str: JSON formatted DuplicateResult string.
    """
    logger.info("MCP Tool search_similar_tickets invoked for: '%s'", title)
    try:
        res = duplicate_service.find_duplicate(title, description, threshold)
        return res.model_dump_json(indent=2)
    except Exception as e:
        logger.error("Error in MCP search_similar_tickets: %s", e)
        return f"Error: {str(e)}"


@mcp.tool()
def get_ticket_template() -> str:
    """
    Retrieve a professional bug report markdown template.
    
    Returns:
        str: Markdown template content.
    """
    logger.info("MCP Tool get_ticket_template invoked.")
    template = """# Bug Report Template

## Title
[Component] Short, descriptive summary of the issue

## Description
A clear and concise description of what the bug is.

## Environment
- OS: [e.g., Windows 11, macOS 14]
- Browser/Platform: [e.g., Chrome 124, iOS App v1.0]
- Version: [e.g., v2.3.1]

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
A clear description of what you expected to happen.

## Actual Behavior
A clear description of what actually happened (include error messages or logs if available).
"""
    return template


@mcp.tool()
def create_github_issue(title: str, body: str) -> str:
    """
    Create a new GitHub issue in the configured repository.
    
    Args:
        title (str): The issue title.
        body (str): The issue description/body in Markdown format.
        
    Returns:
        str: Message confirming issue creation, including number and URL.
    """
    logger.info("MCP Tool create_github_issue invoked for: '%s'", title)
    try:
        github_service = GitHubService()
        res = github_service.create_issue(title, body)
        return f"Issue created successfully!\nNumber: {res.get('number')}\nURL: {res.get('html_url')}"
    except Exception as e:
        logger.error("Error in MCP create_github_issue: %s", e)
        return f"Error: {str(e)}"
