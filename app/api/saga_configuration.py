from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import yaml

from app.core.database import get_db
from app.models import SagaConfiguration, SagaConfigurationStatus
from app.schemas import (
    SagaConfigurationCreate,
    SagaConfigurationUpdate,
    SagaConfigurationResponse,
    SagaConfigurationStatusUpdate,
)

router = APIRouter(prefix="/saga-configurations", tags=["Saga Configurations"])


@router.post("/", response_model=SagaConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_saga_configuration(
    saga_config: SagaConfigurationCreate,
    db: Session = Depends(get_db)
):
    """Create a new saga configuration"""
    # Validate YAML
    try:
        yaml.safe_load(saga_config.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML content: {str(e)}"
        )
    
    # Check if name already exists
    existing = db.query(SagaConfiguration).filter(
        SagaConfiguration.name == saga_config.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saga configuration with name '{saga_config.name}' already exists"
        )
    
    db_saga = SagaConfiguration(**saga_config.model_dump())
    db.add(db_saga)
    db.commit()
    db.refresh(db_saga)
    return db_saga


@router.get("/", response_model=List[SagaConfigurationResponse])
def list_saga_configurations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all saga configurations"""
    sagas = db.query(SagaConfiguration).offset(skip).limit(limit).all()
    return sagas


@router.get("/{saga_id}", response_model=SagaConfigurationResponse)
def get_saga_configuration(
    saga_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific saga configuration by ID"""
    saga = db.query(SagaConfiguration).filter(SagaConfiguration.id == saga_id).first()
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {saga_id} not found"
        )
    return saga


@router.put("/{saga_id}", response_model=SagaConfigurationResponse)
def update_saga_configuration(
    saga_id: int,
    saga_update: SagaConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update a saga configuration"""
    saga = db.query(SagaConfiguration).filter(SagaConfiguration.id == saga_id).first()
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {saga_id} not found"
        )
    
    update_data = saga_update.model_dump(exclude_unset=True)
    
    # Validate YAML if provided
    if "yaml_content" in update_data:
        try:
            yaml.safe_load(update_data["yaml_content"])
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML content: {str(e)}"
            )
    
    # Check name uniqueness if updating name
    if "name" in update_data and update_data["name"] != saga.name:
        existing = db.query(SagaConfiguration).filter(
            SagaConfiguration.name == update_data["name"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Saga configuration with name '{update_data['name']}' already exists"
            )
    
    for field, value in update_data.items():
        setattr(saga, field, value)
    
    db.commit()
    db.refresh(saga)
    return saga


@router.delete("/{saga_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saga_configuration(
    saga_id: int,
    db: Session = Depends(get_db)
):
    """Delete a saga configuration"""
    saga = db.query(SagaConfiguration).filter(SagaConfiguration.id == saga_id).first()
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {saga_id} not found"
        )
    
    db.delete(saga)
    db.commit()
    return None


@router.post("/{saga_id}/enable", response_model=SagaConfigurationResponse)
def enable_saga_configuration(
    saga_id: int,
    db: Session = Depends(get_db)
):
    """Enable a saga configuration"""
    saga = db.query(SagaConfiguration).filter(SagaConfiguration.id == saga_id).first()
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {saga_id} not found"
        )
    
    saga.status = SagaConfigurationStatus.ACTIVE
    db.commit()
    db.refresh(saga)
    return saga


@router.post("/{saga_id}/disable", response_model=SagaConfigurationResponse)
def disable_saga_configuration(
    saga_id: int,
    db: Session = Depends(get_db)
):
    """Disable a saga configuration"""
    saga = db.query(SagaConfiguration).filter(SagaConfiguration.id == saga_id).first()
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga configuration with ID {saga_id} not found"
        )
    
    saga.status = SagaConfigurationStatus.DISABLED
    db.commit()
    db.refresh(saga)
    return saga
