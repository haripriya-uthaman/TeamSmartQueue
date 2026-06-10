from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tickets = relationship("DBTicket", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")


class DBTicket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    environment = Column(Text, nullable=True)
    steps_to_reproduce = Column(Text, nullable=True)       # JSON array string
    expected_result = Column(Text, nullable=True)
    actual_result = Column(Text, nullable=True)
    priority = Column(String(50), nullable=True)           # Low/Medium/High/Critical
    severity = Column(String(50), nullable=True)           # Low/Medium/High/Critical
    module_name = Column(String(255), nullable=True)
    fix_version = Column(String(100), nullable=True)
    affected_version = Column(String(100), nullable=True)
    due_date = Column(String(20), nullable=True)           # ISO date string YYYY-MM-DD
    client = Column(String(255), nullable=True)
    epic = Column(String(255), nullable=True)
    sprint = Column(String(255), nullable=True)
    ocr_text = Column(Text, nullable=True)                 # Extracted text from image attachments
    status = Column(String(50), default="pending")
    score = Column(Float, default=0.0)
    rewritten_title = Column(String(255), nullable=True)
    rewritten_description = Column(String, nullable=True)
    github_issue_url = Column(String(255), nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    affected_count = Column(Integer, default=1, nullable=False)   # incremented when duplicates are found
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("DBUser", back_populates="tickets")
    findings = relationship("DBFinding", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")
    missing_info = relationship("DBMissingInfo", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")
    questions = relationship("DBQuestion", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")


class DBFinding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    finding_text = Column(String, nullable=False)

    ticket = relationship("DBTicket", back_populates="findings")


class DBMissingInfo(Base):
    __tablename__ = "missing_info"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    info_text = Column(String, nullable=False)

    ticket = relationship("DBTicket", back_populates="missing_info")


class DBQuestion(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(50), nullable=False)
    field_or_topic = Column(String(100), nullable=False)
    question_text = Column(String, nullable=False)
    answer_text = Column(String, nullable=True)

    ticket = relationship("DBTicket", back_populates="questions")
