from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uuid
import random

app = FastAPI(title="Mock Payment Service")

# In-memory storage for transactions
transactions = {}


class ChargeRequest(BaseModel):
    amount: float
    currency: str
    customer_id: str
    order_id: str
    payment_method: str


class ChargeResponse(BaseModel):
    status: str
    transaction_id: str
    amount: float


class RefundRequest(BaseModel):
    transaction_id: str
    amount: float


class RefundResponse(BaseModel):
    status: str
    refund_id: str
    amount: float


@app.get("/")
def root():
    return {"service": "Mock Payment Service", "status": "running"}


@app.post("/charge", response_model=ChargeResponse)
def charge_payment(request: ChargeRequest):
    """Process a payment charge"""
    transaction_id = str(uuid.uuid4())
    
    # Simulate payment processing
    # Randomly fail 5% of requests
    if random.random() < 0.05:
        transactions[transaction_id] = {
            "status": "failed",
            "amount": request.amount,
            "customer_id": request.customer_id,
            "order_id": request.order_id
        }
        return ChargeResponse(
            status="failed",
            transaction_id=transaction_id,
            amount=request.amount
        )
    
    transactions[transaction_id] = {
        "status": "charged",
        "amount": request.amount,
        "customer_id": request.customer_id,
        "order_id": request.order_id
    }
    
    return ChargeResponse(
        status="charged",
        transaction_id=transaction_id,
        amount=request.amount
    )


@app.post("/refund", response_model=RefundResponse)
def refund_payment(request: RefundRequest):
    """Process a payment refund (rollback)"""
    if request.transaction_id not in transactions:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    refund_id = str(uuid.uuid4())
    transaction = transactions[request.transaction_id]
    transaction["status"] = "refunded"
    transaction["refund_id"] = refund_id
    
    return RefundResponse(
        status="refunded",
        refund_id=refund_id,
        amount=request.amount
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
