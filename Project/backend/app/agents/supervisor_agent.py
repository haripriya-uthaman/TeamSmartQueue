import logging
from typing import List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.schemas.ticket import (
    TicketSubmission,
    ClarificationResponse,
    AuditResult,
    ClarificationQuestion,
    DuplicateResult,
    RewrittenTicket,
    WorkflowResponse
)
from app.agents.audit_agent import AuditAgent
from app.agents.question_agent import QuestionAgent
from app.agents.rewrite_agent import RewriteAgent
from app.services.duplicate_service import duplicate_service
from app.services.github_service import GitHubService

logger = logging.getLogger(__name__)


class AgentWorkflowState(TypedDict, total=False):
    ticket: TicketSubmission
    answers: List[ClarificationResponse]
    duplicate_threshold: float
    skip_audit: bool
    audit_result: AuditResult
    questions: List[ClarificationQuestion]
    rewritten_ticket: RewrittenTicket
    duplicate_result: DuplicateResult
    github_issue_url: str
    github_issue_number: int
    github_issue_id: str
    status: str


class SupervisorAgent:
    """
    SupervisorAgent coordinates the workflow between the Audit Agent,
    Question Agent, Rewrite Agent, Duplicate Detection, and GitHub Issues API.
    """
    def __init__(self) -> None:
        self.audit_agent = AuditAgent()
        self.question_agent = QuestionAgent()
        self.rewrite_agent = RewriteAgent()
        self.duplicate_service = duplicate_service
        self.github_service = GitHubService()
        self._memory = MemorySaver()
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        Builds the LangGraph state machine used by the supervisor.
        """
        graph = StateGraph(AgentWorkflowState)
        graph.add_node("audit", self._audit_node)
        graph.add_node("questions", self._questions_node)
        graph.add_node("rewrite", self._rewrite_node)
        graph.add_node("duplicate_check", self._duplicate_check_node)
        graph.add_node("github_issue", self._github_issue_node)
        graph.add_node("index_ticket", self._index_ticket_node)

        graph.set_entry_point("audit")
        graph.add_conditional_edges(
            "audit",
            self._route_after_audit,
            {
                "questions": "questions",
                "rewrite": "rewrite",
            },
        )
        graph.add_edge("questions", END)
        graph.add_edge("rewrite", "duplicate_check")
        graph.add_conditional_edges(
            "duplicate_check",
            self._route_after_duplicate_check,
            {
                "duplicate": END,
                "create_issue": "github_issue",
            },
        )
        graph.add_edge("github_issue", "index_ticket")
        graph.add_edge("index_ticket", END)
        return graph.compile(checkpointer=self._memory)

    def _audit_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        if state.get("skip_audit"):
            return {"status": "ready_to_rewrite"}
        return {"audit_result": self.audit_agent.audit_ticket(state["ticket"])}

    def _route_after_audit(self, state: AgentWorkflowState) -> str:
        if state.get("skip_audit"):
            return "rewrite"

        audit_res = state["audit_result"]
        if audit_res.requires_clarification and audit_res.missing_information:
            return "questions"
        return "rewrite"

    def _questions_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        questions = self.question_agent.generate_questions(
            state["ticket"],
            state["audit_result"],
        )
        return {
            "status": "needs_clarification",
            "questions": questions,
        }

    def _rewrite_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        rewritten = self.rewrite_agent.rewrite_ticket(
            state["ticket"],
            state.get("answers", []),
        )
        return {"status": "rewritten", "rewritten_ticket": rewritten}

    def _duplicate_check_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        rewritten = state["rewritten_ticket"]
        dup_res = self.duplicate_service.find_duplicate(
            title=rewritten.rewritten_title,
            description=rewritten.rewritten_description,
            threshold=state.get("duplicate_threshold", 0.85),
        )
        if dup_res.is_duplicate:
            return {"status": "duplicate_found", "duplicate_result": dup_res}
        return {"duplicate_result": dup_res}

    def _route_after_duplicate_check(self, state: AgentWorkflowState) -> str:
        if state["duplicate_result"].is_duplicate:
            return "duplicate"
        return "create_issue"

    def _github_issue_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        rewritten = state["rewritten_ticket"]
        issue_data = self.github_service.create_issue(
            title=rewritten.rewritten_title,
            body=rewritten.rewritten_description,
        )
        return {
            "github_issue_url": issue_data.get("html_url"),
            "github_issue_number": issue_data.get("number"),
            "github_issue_id": str(issue_data.get("id")),
        }

    def _index_ticket_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        rewritten = state["rewritten_ticket"]
        self.duplicate_service.add_ticket(
            ticket_id=state["github_issue_id"],
            title=rewritten.rewritten_title,
            description=rewritten.rewritten_description,
            metadata={
                "github_url": state.get("github_issue_url"),
                "number": state.get("github_issue_number"),
            },
        )
        return {"status": "completed"}

    def _state_to_response(self, state: AgentWorkflowState) -> WorkflowResponse:
        return WorkflowResponse(
            status=state.get("status", "failed"),
            score=state.get("audit_result").score if state.get("audit_result") else None,
            questions=state.get("questions"),
            duplicate_result=state.get("duplicate_result") if state.get("status") == "duplicate_found" else None,
            rewritten_ticket=state.get("rewritten_ticket") if state.get("status") == "completed" else None,
            github_issue_url=state.get("github_issue_url"),
            github_issue_number=state.get("github_issue_number"),
        )

    def _run_graph(
        self,
        ticket: TicketSubmission,
        answers: Optional[List[ClarificationResponse]] = None,
        duplicate_threshold: float = 0.85,
        thread_id: str | None = None,
        skip_audit: bool = False,
    ) -> WorkflowResponse:
        final_state = self._graph.invoke(
            {
                "ticket": ticket,
                "answers": answers or [],
                "duplicate_threshold": duplicate_threshold,
                "skip_audit": skip_audit,
            },
            config={
                "configurable": {
                    "thread_id": thread_id or f"ticket:{ticket.created_at.isoformat()}:{ticket.title}"
                }
            },
        )
        return self._state_to_response(final_state)

    def run_processing_workflow(
        self,
        ticket: TicketSubmission,
        answers: Optional[List[ClarificationResponse]] = None,
        duplicate_threshold: float = 0.85,
        thread_id: str | None = None,
    ) -> WorkflowResponse:
        """
        Runs the post-audit workflow through LangGraph.
        """
        return self._run_graph(
            ticket=ticket,
            answers=answers,
            duplicate_threshold=duplicate_threshold,
            thread_id=thread_id,
            skip_audit=True,
        )

    def run_workflow(
        self, 
        ticket: TicketSubmission, 
        answers: Optional[List[ClarificationResponse]] = None,
        duplicate_threshold: float = 0.85,
        thread_id: str | None = None,
    ) -> WorkflowResponse:
        """
        Coordinates the execution workflow.
        
        If answers are provided, the ticket is rewritten and submitted.
        Otherwise, the ticket is audited first.
        """
        logger.info("Supervisor Agent initiating LangGraph workflow for ticket: '%s'", ticket.title)
        return self._run_graph(
            ticket=ticket,
            answers=answers,
            duplicate_threshold=duplicate_threshold,
            thread_id=thread_id,
        )
