from decimal import Decimal
import os
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import BigInteger, Column, DateTime, Float, JSON, Numeric, func
from sqlmodel import Field, Numeric, Session, SQLModel, create_engine
from uuid import UUID
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file
class Status(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    IN_USE = "in_use"
    
class LLMEnums(str, Enum):
    TOGETHER_AI_Default = "TOGETHER_AI_Default",
    TOGETHER_AI_Llama4 = "TOGETHER_AI_Llama4",
    TOGETHER_AI_Llama4_Scout = "TOGETHER_AI_Llama4_Scout",
    TOGETHER_AI_Gemma = "TOGETHER_AI_Gemma",
    DEEPSEEK_Default = "DEEPSEEK_Default",
    GROQ_Default = "GROQ_Default",
    ANTHROPIC_Default = "ANTHROPIC_Default",
    ANTHROPIC_3_7_Sonnet = "ANTHROPIC_3_7_Sonnet",
    GEMINI_Default = "GEMINI_Default",
    GEMINI_2_FLASH_LITE = "GEMINI_2_FLASH_LITE",
    OPENAI_Default = "OPENAI_Default",
    OPENAI_GPT4o_Mini = "OPENAI_GPT4o_Mini",
    OPENAI_GPT4_1 = "OPENAI_GPT4_1",
    OPENAI_GPT4_1_Mini = "OPENAI_GPT4_1_Mini",
    OPENAI_GPT4_1_Nano = "OPENAI_GPT4_1_Nano",
class PhoneNumberBase(SQLModel):
    e164: str = Field(index=True)
    agentId: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

class PhoneNumber(PhoneNumberBase, table=True):
    __tablename__ = "PhoneNumber"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
    status: Status = Field(default=Status.AVAILABLE, nullable=True)
    projectId: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    is_deleted: bool = Field(default=False, nullable=True)


class PhoneNumberPublic(PhoneNumberBase):
    id: UUID

class ProjectBase(SQLModel):
    name: str = Field(nullable=False)
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id")
    auth_token: str = Field(nullable=False)
    account_sid: str = Field(nullable=False) 
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, nullable=True)
    description: str = Field(nullable=True)
    is_deleted: bool = Field(default=False, nullable=True)
    call_status_webhook: str = Field(nullable=True)
    call_outcome_webhook: str = Field(nullable=True)
    active_agent: Union[UUID, None] = Field(default=None, foreign_key="Agent.id", nullable=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    amount_paid: float = Field(sa_column=Column(Float()), default=None)
    project_metadata: List[str] = Field(sa_column=Column(JSON, nullable=True))

class Project(ProjectBase,table=True):
    __tablename__ = "Projects"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class AgentBase(SQLModel):
    systemInstruction: str = Field(default=None)
    name: str = Field(nullable=False)
    # call_status: str = Field(default="queued", nullable=True)
    is_deleted: bool = Field(default=False, nullable=True)
    voice_id: str = Field(default="9BWtsMINqrJLrRacOk9x", nullable=True)
    stability: Optional[float] = Field(default=None, nullable=True)
    similarity_boost : Optional[float] = Field(default=None, nullable=True)
    optimize_streaming_latency: Optional[str] = Field(default=None, nullable=True)
    style: Optional[float] = Field(default=None, nullable=True)
    use_speaker_boost: Optional[bool] = Field(default=False, nullable=True)
    auto_mode: Optional[bool] = Field(default=False, nullable=True)
    allow_interruptions: Optional[bool] = Field(default=True, nullable=True)
    boosted_keywords: Optional[str] = Field(default=None, nullable=True)
    post_call_questions: List[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    language : Optional[str] = Field(default=None, nullable=True)
    llm : LLMEnums = Field(default=LLMEnums.OPENAI_Default, nullable=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

class Agent(AgentBase, table=True):
    __tablename__ = "Agent"
    projectId: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class UserBase(SQLModel):
    email: str = Field(default=None, nullable=False, unique=True)
    name: str = Field(default=None, nullable=False)
    api_key: str = Field(nullable=True,unique=True)
    password: str = Field(default=None, nullable=False)
    is_deleted: bool = Field(default=False)
    verified: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    active_project: Union[UUID, None] = Field(default=None, nullable=True, foreign_key="Projects.id")
    company_name: str = Field(default=None, nullable=True)
    hubspot_token: str = Field(default=None, nullable=True)
    hubspot_refresh_token: str = Field(default=None, nullable=True)
    hubspot_token_expiry: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

class User(UserBase, table=True):
    __tablename__ = "User"
    id: Union[UUID, None] = Field(default=None, primary_key=True)


class CallQueueBase(SQLModel):
    call_sid: str = Field(default=None, nullable=True, unique=True)
    agent_id: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    project_id: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    call_id: Union[UUID, None] = Field(default=None, foreign_key="call.id")
    status: str = Field(default='queued', nullable=False)
    to_number: str = Field(default=None)
    from_number: str = Field(default=None)
    dynamic_variables: List[str] = Field(sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

class CallQueue(CallQueueBase, table=True):
    __tablename__ = "call_queue"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class CallBase(SQLModel):
    call_sid: str = Field(default=None, nullable=True, unique=True)
    agent_id: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    project_id: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    status: str = Field(default='queued', nullable=False)
    to_number: str = Field(default=None)
    from_number: str = Field(default=None)
    dynamic_variables: List[str] = Field(sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    startTime: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    endTime: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    duration: int = Field(sa_column=Column(BigInteger()), default=None)
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id", nullable=True)
    price: Decimal = Field(default=None, sa_column=Column(Numeric(precision=10, scale=5), default=None))
    priceUnit: str = Field(default=None, nullable=True)
    direction: str = Field(default=None, nullable=True)
    legacy: bool = Field(default=False, nullable=True)
    t_account: str = Field(default=None, nullable=True)
    dial_count: int = Field(default=1, nullable=True)
    metadata_: List[str] = Field(sa_column=Column(JSON, nullable=True))

class Call(CallBase, table=True):
    __tablename__ = "call"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class DynamicBase(SQLModel):
    sid: str = Field(default=None, nullable=True, unique=True)
    vars: List[str] = Field(sa_column=Column(JSON, nullable=False))

class DynamicVariable(DynamicBase,table=True):
    __tablename__ = "Dynamic_Variables"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
    
class EmailVerificationBase(SQLModel):
    email: str = Field(default=None, nullable=False)
    code: str = Field(default=None, nullable=False, unique=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id")

class EmailVerification(EmailVerificationBase,table=True):
    __tablename__ = "email_verifications"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class PasswordResetTokensBase(SQLModel):
    email: str = Field(default=None, nullable=False)
    token: str = Field(default=None, nullable=False, unique=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id")

class PasswordResetTokens(PasswordResetTokensBase,table=True):
    __tablename__ = "password_reset_tokens"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class PaymentsBase(SQLModel):
    amount: float = Field(default=None,sa_column=Column(Numeric))
    price: float = Field(default=None,sa_column=Column(Numeric))
    currency: str = Field(default=None,nullable=False)
    email: str = Field(default=None,nullable=True)
    projectId: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    session_id: str = Field(default=None,nullable=False)
    session_url: str = Field(default=None,nullable=False)
    status: str = Field(default=None,nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    transactionId: Union[UUID, None] = Field(default=None, unique=True)
    
class Payments(PaymentsBase, table=True):
    __tablename__ = "payments"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
    
class SMSBase(SQLModel):
    
    project_id: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    message: str = Field(default=None,nullable=False)
    variables: List[str] = Field(sa_column=Column(JSON))
    meta_data: List[str] = Field(sa_column=Column(JSON))
    from_number: str = Field(default=None,nullable=False)
    direction: str = Field(default=None)
    status: str = Field(default=None)
    type: str = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    
class SMS(SMSBase, table=True):
    __tablename__ = "sms"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
    
    
class HubspotBase(SQLModel):
    call_id: Union[UUID, None] = Field(default=None, foreign_key="call.id")
    systemInstruction: str = Field(default=None)
    project_id: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    agent_id: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    contact_id: int = Field(sa_column=Column(BigInteger))

class Hubspot(HubspotBase,table=True):
    __tablename__ = "hubspot_calls"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class WorkSpacesBase(SQLModel):
    
    name: str = Field(default=None,nullable=False)
    # sms_from_number: str = Field(default=None,nullable=False)
    recipients: List[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    type: int = Field(default=None, nullable=True)
    edges: List[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    nodes: List[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    agent_id: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    project_id: Union[UUID, None] = Field(default=None, foreign_key="Projects.id")
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id")
    fileName: str = Field(default=None, nullable=True)
    batch_count: int = Field(default=None, nullable=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    
class WorkSpaces(WorkSpacesBase,table=True):
    __tablename__ = "workspaces"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class WebCallBase(SQLModel):
    
    agent_id: Union[UUID, None] = Field(default=None, foreign_key="Agent.id")
    dynamic_variables: Union[UUID, None] = Field(default=None, foreign_key="Dynamic_Variables.id", nullable=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    user_id: Union[UUID, None] = Field(default=None, foreign_key="User.id", nullable=True)
    token: str = Field(default=None)
    
class WebCall(WebCallBase, table=True):
    __tablename__ = "web_calls"
    id: Union[UUID, None] = Field(default=None, primary_key=True)

class CallOutcomeBase(SQLModel):
    
    call_id: Union[UUID, None] = Field(default=None, foreign_key="call.id")
    call_outcome: List[str] = Field(sa_column=Column(JSON, nullable=True))
    
class CallOutcome(CallOutcomeBase, table=True):
    __tablename__ = "call_outcomes"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
class ProjectAdminBase(SQLModel):
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    email: str = Field(default=None, nullable=False, unique=True)
    project_id: str = Field(default=None)
    
class ProjectAdmin(ProjectAdminBase, table=True):
    __tablename__ = "ProjectAdmin"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
class CallAnalysisBase(SQLModel):
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    call_id: Union[UUID, None] = Field(default=None, foreign_key="call.id")
    analysis:List[str] = Field(sa_column=Column(JSON)) 
    
class CallAnalysis(CallAnalysisBase, table=True):
    __tablename__ = "CallAnalysis"
    id: Union[UUID, None] = Field(default=None, primary_key=True)
    
print("os.getenv('POSTGRES_URL')................", os.getenv("POSTGRES_URL"))
engine = create_engine(os.getenv("POSTGRES_URL"))


# def create_db_and_tables():
#     SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
