from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DBUser(Base):
    """
    SQL model representing a registered user.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tickets = relationship("DBTicket", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")


class DBTicket(Base):
    """
    SQL model representing a support ticket in the audit pipeline.
    """
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    status = Column(String(50), default="pending")  # needs_clarification, duplicate_found, completed
    score = Column(Float, default=0.0)
    rewritten_title = Column(String(255), nullable=True)
    rewritten_description = Column(String, nullable=True)
    github_issue_url = Column(String(255), nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("DBUser", back_populates="tickets")

    # Relationships
    findings = relationship("DBFinding", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")
    missing_info = relationship("DBMissingInfo", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")
    questions = relationship("DBQuestion", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")


class DBFinding(Base):
    """
    SQL model representing individual audit findings of a ticket.
    """
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    finding_text = Column(String, nullable=False)

    ticket = relationship("DBTicket", back_populates="findings")


class DBMissingInfo(Base):
    """
    SQL model representing topics marked as missing during auditing.
    """
    __tablename__ = "missing_info"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    info_text = Column(String, nullable=False)

    ticket = relationship("DBTicket", back_populates="missing_info")


class DBQuestion(Base):
    """
    SQL model representing generated clarification questions for missing information.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(50), nullable=False)
    field_or_topic = Column(String(100), nullable=False)
    question_text = Column(String, nullable=False)
    answer_text = Column(String, nullable=True)

    ticket = relationship("DBTicket", back_populates="questions")
