import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db, AsyncSessionLocal, DBTicket, DBQuestion, DBFinding, DBMissingInfo
from app.schemas.ticket import (
    TicketSubmission,
    ClarificationResponse,
    WorkflowResponse,
    ClarificationQuestion
)
from app.agents.supervisor_agent import SupervisorAgent
from app.database import DBUser
from app.api.v1.endpoints.auth import get_current_user
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
supervisor = SupervisorAgent()


async def process_ticket_pipeline_task(
    ticket_id: int, 
    title: str, 
    description: str, 
    answers: List[ClarificationResponse] = None
):
    """
    Background worker that handles the slow operations of the supervisor agent workflow:
    Rewriting, duplicate checking, posting to GitHub, and indexing in Chroma vector DB.
    """
    logger.info("Background workflow task started for ticket ID: %d", ticket_id)
    async with AsyncSessionLocal() as db:
        try:
            # Retrieve DB ticket record
            result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
            db_ticket = result.scalars().first()
            if not db_ticket:
                logger.error("Ticket ID %d not found in background task", ticket_id)
                return
            
            # Reconstruct submission
            submission = TicketSubmission(title=title, description=description)
            
            # Run the LangGraph supervisor for rewrite, duplicate check, GitHub issue creation, and vector indexing.
            logger.info("Running LangGraph processing workflow for ticket ID %d...", ticket_id)
            workflow_res = await asyncio.to_thread(
                supervisor.run_processing_workflow,
                submission,
                answers or [],
                0.85,
                f"ticket:{ticket_id}",
            )

            if workflow_res.status == "duplicate_found":
                duplicate_id = (
                    workflow_res.duplicate_result.duplicate_ticket_id
                    if workflow_res.duplicate_result
                    else None
                )
                logger.info("Duplicate found for ticket ID %d matching ID %s", ticket_id, duplicate_id)
                db_ticket.status = "duplicate_found"
                db_ticket.score = 0.0
                await db.commit()
                return

            if workflow_res.status != "completed" or not workflow_res.rewritten_ticket:
                raise RuntimeError(f"Unexpected workflow status: {workflow_res.status}")
            
            # 5. Update DB ticket
            db_ticket.status = "completed"
            db_ticket.score = 100.0  # Pass threshold
            db_ticket.rewritten_title = workflow_res.rewritten_ticket.rewritten_title
            db_ticket.rewritten_description = workflow_res.rewritten_ticket.rewritten_description
            db_ticket.github_issue_url = workflow_res.github_issue_url
            db_ticket.github_issue_number = workflow_res.github_issue_number
            
            await db.commit()
            logger.info("Background workflow task completed successfully for ticket ID: %d", ticket_id)
            
        except Exception as e:
            logger.error("Background workflow task failed for ticket ID: %d: %s", ticket_id, e, exc_info=True)
            try:
                result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
                db_ticket = result.scalars().first()
                if db_ticket:
                    db_ticket.status = "failed"
                    await db.commit()
            except Exception as db_err:
                logger.error("Failed to mark ticket %d as failed: %s", ticket_id, db_err)


@router.post("/submit", response_model=WorkflowResponse)
async def submit_ticket(
    submission: TicketSubmission, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """
    Submits a new support ticket, runs synchronous audit agent, and offloads
    slow processing (rewrite/duplicate checks/GitHub) to a background worker.
    """
    logger.info("API Submit called for ticket: '%s'", submission.title)
    
    # 1. Create a DB ticket record in pending status
    db_ticket = DBTicket(
        user_id=current_user.id,
        title=submission.title,
        description=submission.description,
        status="pending"
    )
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    
    try:
        # 2. Run Audit Agent synchronously (Run in thread to prevent blocking event loop)
        logger.info("Running Audit Agent synchronously for ticket ID %d...", db_ticket.id)
        audit_res = await asyncio.to_thread(
            supervisor.audit_agent.audit_ticket,
            submission
        )
        db_ticket.score = audit_res.score
        
        # Save findings
        for finding in audit_res.findings:
            db_finding = DBFinding(
                ticket_id=db_ticket.id,
                finding_text=finding
            )
            db.add(db_finding)
            
        # Save missing info
        for missing in audit_res.missing_information:
            db_missing = DBMissingInfo(
                ticket_id=db_ticket.id,
                info_text=missing
            )
            db.add(db_missing)
            
        # 3. Determine next workflow steps
        if audit_res.requires_clarification and audit_res.missing_information:
            logger.info("Ticket ID %d requires clarification. Generating questions...", db_ticket.id)
            questions = supervisor.question_agent.generate_questions(submission, audit_res)
            
            # Save questions
            for q in questions:
                db_q = DBQuestion(
                    ticket_id=db_ticket.id,
                    question_id=q.question_id,
                    field_or_topic=q.field_or_topic,
                    question_text=q.question_text
                )
                db.add(db_q)
                
            db_ticket.status = "needs_clarification"
            await db.commit()
            await db.refresh(db_ticket)
            
            return WorkflowResponse(
                status="needs_clarification",
                ticket_id=db_ticket.id,
                score=audit_res.score,
                questions=[
                    ClarificationQuestion(
                        question_id=q.question_id,
                        field_or_topic=q.field_or_topic,
                        question_text=q.question_text
                    ) for q in questions
                ]
            )
            
        else:
            # Proceed to processing in background
            logger.info("Ticket ID %d passed audit. Queueing background processing task...", db_ticket.id)
            db_ticket.status = "processing"
            await db.commit()
            await db.refresh(db_ticket)
            
            background_tasks.add_task(
                process_ticket_pipeline_task, 
                db_ticket.id, 
                submission.title, 
                submission.description
            )
            
            return WorkflowResponse(
                status="processing",
                ticket_id=db_ticket.id,
                score=audit_res.score
            )
            
    except Exception as e:
        logger.error("API submission failed for ticket: %s", e, exc_info=True)
        db_ticket.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline loop workflow failed: {str(e)}"
        )


@router.post("/{ticket_id}/clarify", response_model=WorkflowResponse)
async def clarify_ticket(
    ticket_id: int, 
    answers: List[ClarificationResponse], 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """
    Accepts user answers to clarifying questions, updates DB questions, and resumes workflow in background.
    """
    logger.info("API Clarify called for ticket ID: %d", ticket_id)
    
    result = await db.execute(
        select(DBTicket).where(DBTicket.id == ticket_id, DBTicket.user_id == current_user.id)
    )
    db_ticket = result.scalars().first()
    
    if not db_ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
        
    if db_ticket.status != "needs_clarification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="This ticket does not require clarification."
        )
        
    # Map answers by question_id and save to DB
    answers_dict = {ans.question_id: ans.answer_text for ans in answers}
    for q in db_ticket.questions:
        if q.question_id in answers_dict:
            q.answer_text = answers_dict[q.question_id]
            
    # Transition to processing state
    db_ticket.status = "processing"
    await db.commit()
    await db.refresh(db_ticket)
    
    # Run the rest of the workflow in a background task
    background_tasks.add_task(
        process_ticket_pipeline_task,
        db_ticket.id,
        db_ticket.title,
        db_ticket.description,
        answers
    )
    
    return WorkflowResponse(
        status="processing",
        ticket_id=db_ticket.id
    )


@router.get("/", response_model=List[dict])
async def list_tickets(db: AsyncSession = Depends(get_db), current_user: DBUser = Depends(get_current_user)):
    """
    Lists all ticket submissions in the database.
    """
    result = await db.execute(select(DBTicket).where(DBTicket.user_id == current_user.id).order_by(DBTicket.created_at.desc()))
    tickets = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "score": t.score,
            "rewritten_title": t.rewritten_title,
            "github_issue_url": t.github_issue_url,
            "github_issue_number": t.github_issue_number,
            "created_at": t.created_at.isoformat()
        } for t in tickets
    ]


@router.get("/{ticket_id}", response_model=dict)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: DBUser = Depends(get_current_user)):
    """
    Retrieves details for a specific ticket.
    """
    result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id, DBTicket.user_id == current_user.id))
    t = result.scalars().first()
    
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
        
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "score": t.score,
        "rewritten_title": t.rewritten_title,
        "rewritten_description": t.rewritten_description,
        "github_issue_url": t.github_issue_url,
        "github_issue_number": t.github_issue_number,
        "created_at": t.created_at.isoformat(),
        "questions": [
            {
                "question_id": q.question_id,
                "field_or_topic": q.field_or_topic,
                "question_text": q.question_text,
                "answer_text": q.answer_text
            } for q in t.questions
        ],
        "findings": [f.finding_text for f in t.findings],
        "missing_information": [m.info_text for m in t.missing_info]
    }
