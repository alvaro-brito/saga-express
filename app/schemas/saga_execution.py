from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.saga_execution import SagaExecutionStatus, SagaExecutionStepStatus


class SagaExecutionStepResponse(BaseModel):
    id: int
    step_name: str
    step_type: str
    status: SagaExecutionStepStatus
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SagaExecutionResponse(BaseModel):
    id: int
    saga_configuration_id: int
    correlation_id: str
    status: SagaExecutionStatus
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[SagaExecutionStepResponse] = []
    
    class Config:
        from_attributes = True


class SagaExecutionCreate(BaseModel):
    input_data: Dict[str, Any] = Field(..., description="Input data for saga execution")


class SagaTestRequest(BaseModel):
    saga_configuration_id: int = Field(..., description="ID of the saga configuration to test")
    input_data: Dict[str, Any] = Field(..., description="Test input data")
