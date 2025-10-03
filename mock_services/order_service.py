from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import random

app = FastAPI(title="Mock Order Service")


class ValidateOrderRequest(BaseModel):
    order_id: str
    customer_id: str
    items: List[Dict[str, Any]]


class ValidateOrderResponse(BaseModel):
    valid: bool
    order_id: str
    total_amount: float


@app.get("/")
def root():
    return {"service": "Mock Order Service", "status": "running"}


@app.post("/validate", response_model=ValidateOrderResponse)
def validate_order(request: ValidateOrderRequest):
    """Validate an order"""
    # Calculate total amount
    total_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in request.items)
    
    # Simulate validation logic
    is_valid = total_amount > 0 and len(request.items) > 0
    
    # Randomly fail 10% of requests for testing
    if random.random() < 0.1:
        is_valid = False
    
    return ValidateOrderResponse(
        valid=is_valid,
        order_id=request.order_id,
        total_amount=total_amount
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
