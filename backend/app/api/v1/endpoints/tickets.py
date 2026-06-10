import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db, AsyncSessionLocal, DBTicket, DBQuestion, DBFinding, DBMissingInfo
from app.schemas.ticket import (
    TicketSubmission,
    TicketUpdate,
    ClarificationResponse,
    WorkflowResponse,
    ClarificationQuestion
)
from app.agents.supervisor_agent import SupervisorAgent
from app.database import DBUser
from app.api.v1.endpoints.auth import get_current_user
from app.services.ai_service import ai_service as gemini_service
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
supervisor = SupervisorAgent()


def _ticket_to_dict(t: DBTicket) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "environment": t.environment,
        "steps_to_reproduce": json.loads(t.steps_to_reproduce) if t.steps_to_reproduce else None,
        "expected_result": t.expected_result,
        "actual_result": t.actual_result,
        "priority": t.priority,
        "severity": t.severity,
        "module_name": t.module_name,
        "fix_version": t.fix_version,
        "affected_version": t.affected_version,
        "due_date": t.due_date,
        "client": t.client,
        "epic": t.epic,
        "sprint": t.sprint,
        "ocr_text": t.ocr_text,
        "status": t.status,
        "score": t.score,
        "rewritten_title": t.rewritten_title,
        "rewritten_description": t.rewritten_description,
        "github_issue_url": t.github_issue_url,
        "github_issue_number": t.github_issue_number,
        "affected_count": t.affected_count if t.affected_count is not None else 1,
        "created_at": t.created_at.isoformat(),
    }


def _ticket_to_detail_dict(t: DBTicket) -> dict:
    d = _ticket_to_dict(t)
    d.update({
        "questions": [
            {
                "question_id": q.question_id,
                "field_or_topic": q.field_or_topic,
                "question_text": q.question_text,
                "answer_text": q.answer_text,
            }
            for q in t.questions
        ],
        "findings": [f.finding_text for f in t.findings],
        "missing_information": [m.info_text for m in t.missing_info],
    })
    return d


def _build_submission(db_ticket: DBTicket) -> TicketSubmission:
    """Reconstruct a TicketSubmission from a DB row (used in background tasks)."""
    steps = json.loads(db_ticket.steps_to_reproduce) if db_ticket.steps_to_reproduce else None
    return TicketSubmission(
        title=db_ticket.title,
        description=db_ticket.description,
        environment=db_ticket.environment,
        steps_to_reproduce=steps,
        expected_result=db_ticket.expected_result,
        actual_result=db_ticket.actual_result,
        priority=db_ticket.priority,
        severity=db_ticket.severity,
        module_name=db_ticket.module_name,
        fix_version=db_ticket.fix_version,
        affected_version=db_ticket.affected_version,
        due_date=db_ticket.due_date,
        client=db_ticket.client,
        epic=db_ticket.epic,
        sprint=db_ticket.sprint,
    )


async def run_audit_and_route(ticket_id: int, attachments: List[str] = None):
    """
    Background task: OCR → Audit → route to needs_clarification or processing.
    Returns immediately so the submit endpoint is non-blocking.
    """
    logger.info("Background audit started for ticket ID: %d", ticket_id)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
            db_ticket = result.scalars().first()
            if not db_ticket:
                logger.error("Ticket ID %d not found in audit background task", ticket_id)
                return

            # 1. OCR (tolerated failure)
            ocr_text = ""
            if attachments:
                logger.info("Running OCR on %d attachment(s) for ticket ID %d", len(attachments), ticket_id)
                try:
                    ocr_text = await asyncio.to_thread(
                        gemini_service.extract_text_from_images, attachments
                    )
                    db_ticket.ocr_text = ocr_text or None
                    await db.commit()
                except Exception as exc:
                    logger.warning("OCR extraction failed (non-fatal): %s", exc)

            # 2. Build submission + run Audit
            submission = _build_submission(db_ticket)
            logger.info("Running Audit Agent for ticket ID %d", ticket_id)
            audit_res = await asyncio.to_thread(
                supervisor.audit_agent.audit_ticket, submission, ocr_text
            )
            db_ticket.score = audit_res.score

            for finding in audit_res.findings:
                db.add(DBFinding(ticket_id=ticket_id, finding_text=finding))
            for missing in audit_res.missing_information:
                db.add(DBMissingInfo(ticket_id=ticket_id, info_text=missing))

            # 3. Route
            if audit_res.requires_clarification and audit_res.missing_information:
                logger.info("Ticket ID %d requires clarification.", ticket_id)
                questions = supervisor.question_agent.generate_questions(submission, audit_res)
                for q in questions:
                    db.add(DBQuestion(
                        ticket_id=ticket_id,
                        question_id=q.question_id,
                        field_or_topic=q.field_or_topic,
                        question_text=q.question_text,
                    ))
                db_ticket.status = "needs_clarification"
                await db.commit()
            else:
                logger.info("Ticket ID %d passed audit. Launching pipeline.", ticket_id)
                db_ticket.status = "processing"
                await db.commit()
                # Run pipeline in same background coroutine (opens its own session)
                await process_ticket_pipeline_task(ticket_id)

        except Exception as e:
            logger.error("Audit/route failed for ticket ID %d: %s", ticket_id, e, exc_info=True)
            try:
                async with AsyncSessionLocal() as err_db:
                    r = await err_db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
                    t = r.scalars().first()
                    if t:
                        t.status = "failed"
                        t.error_message = str(e)
                        await err_db.commit()
            except Exception as db_err:
                logger.error("Failed to mark ticket %d as failed: %s", ticket_id, db_err)


async def process_ticket_pipeline_task(
    ticket_id: int,
    answers: List[ClarificationResponse] = None
):
    logger.info("Pipeline task started for ticket ID: %d", ticket_id)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
            db_ticket = result.scalars().first()
            if not db_ticket:
                logger.error("Ticket ID %d not found in pipeline task", ticket_id)
                return

            submission = _build_submission(db_ticket)

            logger.info("Running LangGraph workflow for ticket ID %d", ticket_id)
            workflow_res = await asyncio.to_thread(
                supervisor.run_processing_workflow,
                submission,
                answers or [],
                0.85,
                f"ticket:{ticket_id}",
            )

            if workflow_res.status == "duplicate_found":
                logger.info("Duplicate found for ticket ID %d", ticket_id)
                db_ticket.status = "duplicate_found"
                db_ticket.score = 0.0

                # ── Aggregate: bump original ticket's affected_count + priority ──
                dup_id_raw = (
                    workflow_res.duplicate_result.duplicate_ticket_id
                    if workflow_res.duplicate_result else None
                )
                if dup_id_raw:
                    try:
                        # ChromaDB IDs are stored as "ticket:N" or just "N"
                        orig_id = int(dup_id_raw.split(":")[-1])
                        orig_res = await db.execute(
                            select(DBTicket).where(DBTicket.id == orig_id)
                        )
                        orig = orig_res.scalars().first()
                        if orig:
                            orig.affected_count = (orig.affected_count or 1) + 1
                            # Priority ladder: Low < Medium < High < Critical
                            priority_ladder = ["Low", "Medium", "High", "Critical"]
                            if orig.affected_count >= 3:
                                orig.priority = "Critical"
                            elif orig.affected_count == 2:
                                cur_idx = priority_ladder.index(orig.priority) if orig.priority in priority_ladder else 1
                                orig.priority = priority_ladder[max(cur_idx, 2)]  # at least High
                            logger.info(
                                "Original ticket ID %d affected_count=%d priority bumped to %s",
                                orig_id, orig.affected_count, orig.priority
                            )
                    except Exception as agg_err:
                        logger.warning("Duplicate aggregation failed (non-fatal): %s", agg_err)

                await db.commit()
                return

            if workflow_res.status != "completed" or not workflow_res.rewritten_ticket:
                raise RuntimeError(f"Unexpected workflow status: {workflow_res.status}")

            db_ticket.status = "completed"
            db_ticket.score = 100.0
            db_ticket.rewritten_title = workflow_res.rewritten_ticket.rewritten_title
            db_ticket.rewritten_description = workflow_res.rewritten_ticket.rewritten_description
            db_ticket.github_issue_url = workflow_res.github_issue_url
            db_ticket.github_issue_number = workflow_res.github_issue_number

            await db.commit()
            logger.info("Pipeline completed for ticket ID: %d", ticket_id)

        except Exception as e:
            logger.error("Pipeline failed for ticket ID %d: %s", ticket_id, e, exc_info=True)
            try:
                result = await db.execute(select(DBTicket).where(DBTicket.id == ticket_id))
                db_ticket = result.scalars().first()
                if db_ticket:
                    db_ticket.status = "failed"
                    db_ticket.error_message = str(e)
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
    Creates ticket immediately and returns ticket_id.
    OCR + Audit + routing run in the background — zero wait for the user.
    """
    logger.info("API Submit: '%s' by user %d", submission.title, current_user.id)

    db_ticket = DBTicket(
        user_id=current_user.id,
        title=submission.title,
        description=submission.description,
        environment=submission.environment,
        steps_to_reproduce=json.dumps(submission.steps_to_reproduce) if submission.steps_to_reproduce else None,
        expected_result=submission.expected_result,
        actual_result=submission.actual_result,
        priority=submission.priority,
        severity=submission.severity,
        module_name=submission.module_name,
        fix_version=submission.fix_version,
        affected_version=submission.affected_version,
        due_date=submission.due_date,
        client=submission.client,
        epic=submission.epic,
        sprint=submission.sprint,
        status="pending",
    )
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)

    background_tasks.add_task(run_audit_and_route, db_ticket.id, submission.attachments)

    return WorkflowResponse(status="pending", ticket_id=db_ticket.id)


@router.post("/{ticket_id}/clarify", response_model=WorkflowResponse)
async def clarify_ticket(
    ticket_id: int,
    answers: List[ClarificationResponse],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    logger.info("API Clarify for ticket ID: %d", ticket_id)

    result = await db.execute(
        select(DBTicket).where(DBTicket.id == ticket_id, DBTicket.user_id == current_user.id)
    )
    db_ticket = result.scalars().first()

    if not db_ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    if db_ticket.status != "needs_clarification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This ticket does not require clarification.",
        )

    answers_dict = {ans.question_id: ans.answer_text for ans in answers}
    for q in db_ticket.questions:
        if q.question_id in answers_dict:
            q.answer_text = answers_dict[q.question_id]

    db_ticket.status = "processing"
    await db.commit()
    await db.refresh(db_ticket)

    background_tasks.add_task(process_ticket_pipeline_task, db_ticket.id, answers)

    return WorkflowResponse(status="processing", ticket_id=db_ticket.id)


@router.patch("/{ticket_id}", response_model=dict)
async def update_ticket(
    ticket_id: int,
    updates: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    result = await db.execute(
        select(DBTicket).where(DBTicket.id == ticket_id, DBTicket.user_id == current_user.id)
    )
    t = result.scalars().first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    if t.status == "processing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit while processing.")

    # Allowed manual status transitions
    MANUAL_TRANSITIONS = {
        "pending":             ["closed"],
        "needs_clarification": ["closed"],
        "completed":           ["closed"],
        "failed":              ["pending", "closed"],
        "duplicate_found":     ["pending", "closed"],
        "closed":              ["pending"],
    }

    data = updates.model_dump(exclude_unset=True)
    requested_status = data.pop("status", None)

    for field, value in data.items():
        if field == "steps_to_reproduce":
            setattr(t, field, json.dumps(value) if value else None)
        else:
            setattr(t, field, value)

    # Apply manual status transition
    if requested_status:
        allowed = MANUAL_TRANSITIONS.get(t.status, [])
        if requested_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{t.status}' to '{requested_status}'.",
            )
        t.status = requested_status
    elif t.status in ("needs_clarification", "failed"):
        # Re-queue for audit when fields are edited
        t.status = "pending"

    await db.commit()
    await db.refresh(t)
    return _ticket_to_detail_dict(t)


@router.get("/", response_model=List[dict])
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    result = await db.execute(
        select(DBTicket)
        .where(DBTicket.user_id == current_user.id)
        .order_by(DBTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    return [_ticket_to_dict(t) for t in tickets]


@router.get("/{ticket_id}", response_model=dict)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    result = await db.execute(
        select(DBTicket).where(DBTicket.id == ticket_id, DBTicket.user_id == current_user.id)
    )
    t = result.scalars().first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return _ticket_to_detail_dict(t)
