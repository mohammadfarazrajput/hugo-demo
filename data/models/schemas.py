# data/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Material(BaseModel):
    material_id: str
    description: str
    category: str
    unit: str
    unit_price: float

class StockLevel(BaseModel):
    material_id: str
    current_stock: float
    reserved_stock: float
    available_stock: float
    warehouse_location: str

class MaterialOrder(BaseModel):
    order_id: str
    material_id: str
    supplier_id: str
    quantity: float
    order_date: str
    delivery_date: str
    status: str
    unit_price: float

class SalesOrder(BaseModel):
    order_id: str
    order_date: str
    customer_type: str
    scooter_model: str
    quantity: int
    status: str

class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    contact_email: str
    lead_time_days: int
    reliability_score: float

class DispatchParameter(BaseModel):
    material_id: str
    reorder_point: float
    safety_stock: float
    lot_size: float
    max_stock: float

class BOMItem(BaseModel):
    material_id: str
    quantity: int

class ScooterSpec(BaseModel):
    model: str
    bom: List[BOMItem]
    specifications: Dict[str, Any] = {}

class EmailData(BaseModel):
    filename: str
    subject: str
    sender: str
    date: str
    body: str
    email_type: str
    extracted_info: Dict[str, Any]

class HugoQuery(BaseModel):
    question: str

class HugoResponse(BaseModel):
    answer: str
    data: Optional[Dict[str, Any]] = None
    alerts: Optional[List[str]] = None
    thinking: Optional[str] = None

class Alert(BaseModel):
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    material_id: Optional[str] = None
    order_id: Optional[str] = None
    action_required: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class BuildCapacity(BaseModel):
    scooter_model: str
    max_units: int
    bottleneck_materials: List[Dict[str, Any]]
    sufficient_materials: List[str]