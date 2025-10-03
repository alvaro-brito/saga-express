from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import SagaExecution, SagaConfiguration, SagaConfigurationStatus
from app.schemas import (
    SagaExecutionResponse,
    SagaTestRequest,
)
from app.services.saga_executor import SagaExecutor

router = APIRouter(prefix="/saga-executions", tags=["Saga Executions"])


@router.post("/test", response_model=SagaExecutionResponse)
async def test_saga_configuration(
    test_request: SagaTestRequest,
    db: Session = Depends(get_db)
):
    """Test a saga configuration with provided input data"""
    # Get saga configuration
    saga_config = db.query(SagaConfiguration).filter(
        SagaConfiguration.id == test_request.saga_configuration_id
    ).first()
    
    if not saga_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {test_request.saga_configuration_id} not found"
        )
    
    if saga_config.status != SagaConfigurationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saga configuration is not active (current status: {saga_config.status})"
        )
    
    # Execute saga
    executor = SagaExecutor(db)
    execution = await executor.execute_saga(saga_config, test_request.input_data)
    
    return execution


@router.get("/", response_model=List[SagaExecutionResponse])
def list_saga_executions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all saga executions"""
    executions = db.query(SagaExecution).offset(skip).limit(limit).all()
    return executions


@router.get("/{execution_id}", response_model=SagaExecutionResponse)
def get_saga_execution(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific saga execution by ID"""
    execution = db.query(SagaExecution).filter(SagaExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga execution with ID {execution_id} not found"
        )
    return execution


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saga_execution(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """Delete a saga execution"""
    execution = db.query(SagaExecution).filter(SagaExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga execution with ID {execution_id} not found"
        )
    
    db.delete(execution)
    db.commit()
    return None
