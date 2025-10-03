from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import random

app = FastAPI(title="Mock Inventory Service")

# In-memory storage for reservations
reservations = {}


class ReserveInventoryRequest(BaseModel):
    order_id: str
    items: List[Dict[str, Any]]
    reservation_timeout: str


class ReserveInventoryResponse(BaseModel):
    reservation_id: str
    reserved_items: List[Dict[str, Any]]


class ConfirmInventoryRequest(BaseModel):
    reservation_id: str
    order_id: str


class ConfirmInventoryResponse(BaseModel):
    confirmed_items: List[Dict[str, Any]]


class CancelReservationRequest(BaseModel):
    reservation_id: str


@app.get("/")
def root():
    return {"service": "Mock Inventory Service", "status": "running"}


@app.post("/reserve", response_model=ReserveInventoryResponse)
def reserve_inventory(request: ReserveInventoryRequest):
    """Reserve inventory for an order"""
    reservation_id = str(uuid.uuid4())
    
    # Simulate inventory check
    reserved_items = []
    for item in request.items:
        reserved_items.append({
            "item_id": item.get("item_id", "unknown"),
            "quantity": item.get("quantity", 1),
            "reserved": True
        })
    
    # Store reservation
    reservations[reservation_id] = {
        "order_id": request.order_id,
        "items": reserved_items,
        "status": "reserved"
    }
    
    # Randomly fail 5% of requests
    if random.random() < 0.05:
        raise HTTPException(status_code=409, detail="Insufficient inventory")
    
    return ReserveInventoryResponse(
        reservation_id=reservation_id,
        reserved_items=reserved_items
    )


@app.post("/confirm", response_model=ConfirmInventoryResponse)
def confirm_inventory(request: ConfirmInventoryRequest):
    """Confirm inventory reservation"""
    if request.reservation_id not in reservations:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    reservation = reservations[request.reservation_id]
    reservation["status"] = "confirmed"
    
    return ConfirmInventoryResponse(
        confirmed_items=reservation["items"]
    )


@app.delete("/cancel-reservation")
def cancel_reservation(request: CancelReservationRequest):
    """Cancel inventory reservation (rollback)"""
    if request.reservation_id in reservations:
        del reservations[request.reservation_id]
    
    return {"status": "cancelled"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
