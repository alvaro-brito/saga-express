from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class SagaExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SagaExecution(Base):
    __tablename__ = "saga_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    saga_configuration_id = Column(Integer, ForeignKey("saga_configurations.id"), nullable=False)
    correlation_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(
        SQLEnum(SagaExecutionStatus),
        default=SagaExecutionStatus.PENDING,
        nullable=False
    )
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    steps = relationship("SagaExecutionStep", back_populates="execution", cascade="all, delete-orphan")


class SagaExecutionStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class SagaExecutionStep(Base):
    __tablename__ = "saga_execution_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    saga_execution_id = Column(Integer, ForeignKey("saga_executions.id"), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)  # api or kafka
    status = Column(
        SQLEnum(SagaExecutionStepStatus),
        default=SagaExecutionStepStatus.PENDING,
        nullable=False
    )
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    execution = relationship("SagaExecution", back_populates="steps")
