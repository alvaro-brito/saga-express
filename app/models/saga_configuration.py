from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SagaConfigurationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class SagaConfiguration(Base):
    __tablename__ = "saga_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    yaml_content = Column(Text, nullable=False)
    status = Column(
        SQLEnum(SagaConfigurationStatus),
        default=SagaConfigurationStatus.ACTIVE,
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
