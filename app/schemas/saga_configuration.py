from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.saga_configuration import SagaConfigurationStatus


class SagaConfigurationBase(BaseModel):
    name: str = Field(..., description="Unique name for the saga configuration")
    version: str = Field(..., description="Version of the saga configuration")
    description: Optional[str] = Field(None, description="Description of the saga")
    yaml_content: str = Field(..., description="YAML content of the saga configuration")


class SagaConfigurationCreate(SagaConfigurationBase):
    pass


class SagaConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    yaml_content: Optional[str] = None


class SagaConfigurationResponse(SagaConfigurationBase):
    id: int
    status: SagaConfigurationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SagaConfigurationStatusUpdate(BaseModel):
    status: SagaConfigurationStatus
