# backend/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    data: Optional[Dict[str, Any]] = None
    alerts: Optional[List[str]] = None

class AlertResponse(BaseModel):
    total_alerts: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    alerts: List[Dict[str, Any]]

class BuildCapacityRequest(BaseModel):
    scooter_model: str

class OptimizationRequest(BaseModel):
    material_id: Optional[str] = None

# These will be set from main.py
analytical_agent = None
reactive_agent = None
optimization_agent = None
bom_service = None
inventory_service = None
csv_processor = None
email_processor = None

def set_agents(analytical, reactive, optimization, bom, inventory, csv, email):
    """Set the agent instances"""
    global analytical_agent, reactive_agent, optimization_agent
    global bom_service, inventory_service, csv_processor, email_processor
    
    analytical_agent = analytical
    reactive_agent = reactive
    optimization_agent = optimization
    bom_service = bom
    inventory_service = inventory
    csv_processor = csv
    email_processor = email

@router.post("/chat", response_model=ChatResponse)
async def chat_with_hugo(request: ChatRequest):
    """Chat with Hugo - ask any operational question"""
    try:
        if not analytical_agent:
            raise HTTPException(status_code=500, detail="Hugo is not initialized")
        
        response = await analytical_agent.answer_question(request.question)
        
        return ChatResponse(
            answer=response.get('answer', 'No response generated'),
            data=response.get('data'),
            alerts=None
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=AlertResponse)
async def get_alerts():
    """Get all current alerts and risks"""
    try:
        if not reactive_agent:
            raise HTTPException(status_code=500, detail="Reactive agent not initialized")
        
        alert_summary = reactive_agent.get_alert_summary()
        
        return AlertResponse(
            total_alerts=alert_summary['total_alerts'],
            by_severity=alert_summary['by_severity'],
            by_type=alert_summary['by_type'],
            alerts=alert_summary['alerts']
        )
    except Exception as e:
        logger.error(f"Error generating alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/build-capacity")
async def get_build_capacity(request: BuildCapacityRequest):
    """Calculate build capacity for a scooter model"""
    try:
        if not bom_service:
            raise HTTPException(status_code=500, detail="BOM service not initialized")
        
        capacity = bom_service.calculate_build_capacity(request.scooter_model)
        
        return capacity
    except Exception as e:
        logger.error(f"Error calculating build capacity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory-summary")
async def get_inventory_summary():
    """Get inventory summary statistics"""
    try:
        if not inventory_service:
            raise HTTPException(status_code=500, detail="Inventory service not initialized")
        
        summary = inventory_service.get_inventory_summary()
        
        return summary
    except Exception as e:
        logger.error(f"Error getting inventory summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/low-stock")
async def get_low_stock_materials():
    """Get materials with low stock levels"""
    try:
        if not csv_processor:
            raise HTTPException(status_code=500, detail="CSV processor not initialized")
        
        low_stock = csv_processor.get_low_stock_materials()
        
        return {
            'count': len(low_stock),
            'materials': low_stock
        }
    except Exception as e:
        logger.error(f"Error getting low stock materials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reorder-recommendations")
async def get_reorder_recommendations():
    """Get reorder recommendations"""
    try:
        if not inventory_service:
            raise HTTPException(status_code=500, detail="Inventory service not initialized")
        
        recommendations = inventory_service.get_reorder_recommendations()
        
        return {
            'count': len(recommendations),
            'recommendations': recommendations
        }
    except Exception as e:
        logger.error(f"Error getting reorder recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supplier-performance")
async def get_supplier_performance():
    """Get supplier performance analysis"""
    try:
        if not csv_processor:
            raise HTTPException(status_code=500, detail="CSV processor not initialized")
        
        performance = csv_processor.get_supplier_performance()
        
        return {
            'suppliers': performance
        }
    except Exception as e:
        logger.error(f"Error getting supplier performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emails")
async def get_emails():
    """Get parsed supplier emails"""
    try:
        if not email_processor:
            raise HTTPException(status_code=500, detail="Email processor not initialized")
        
        emails = email_processor.parse_all_emails()
        critical = email_processor.get_critical_emails(emails)
        
        return {
            'total_emails': len(emails),
            'critical_emails': len(critical),
            'emails': emails,
            'critical': critical
        }
    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_dispatch_parameters(request: OptimizationRequest):
    """Optimize inventory dispatch parameters"""
    try:
        if not optimization_agent:
            raise HTTPException(status_code=500, detail="Optimization agent not initialized")
        
        optimization = await optimization_agent.optimize_inventory_parameters(request.material_id)
        
        return optimization
    except Exception as e:
        logger.error(f"Error optimizing parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-optimization")
async def get_cost_optimization():
    """Get cost optimization suggestions"""
    try:
        if not optimization_agent:
            raise HTTPException(status_code=500, detail="Optimization agent not initialized")
        
        optimization = await optimization_agent.suggest_cost_optimization()
        
        return optimization
    except Exception as e:
        logger.error(f"Error getting cost optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stockout-risks")
async def get_stockout_risks():
    """Get materials at risk of stockout"""
    try:
        if not inventory_service:
            raise HTTPException(status_code=500, detail="Inventory service not initialized")
        
        risks = inventory_service.forecast_stockout_risk(30)
        
        return {
            'count': len(risks),
            'risks': risks
        }
    except Exception as e:
        logger.error(f"Error getting stockout risks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock-health")
async def get_stock_health():
    """Get stock health analysis for all materials"""
    try:
        if not inventory_service:
            raise HTTPException(status_code=500, detail="Inventory service not initialized")
        
        health = inventory_service.analyze_stock_health()
        
        # Group by health status
        by_status = {}
        for item in health:
            status = item['health_status']
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(item)
        
        return {
            'total_materials': len(health),
            'by_status': {k: len(v) for k, v in by_status.items()},
            'materials': health,
            'grouped': by_status
        }
    except Exception as e:
        logger.error(f"Error getting stock health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales-orders")
async def get_sales_orders():
    """Get sales orders summary"""
    try:
        if not csv_processor:
            raise HTTPException(status_code=500, detail="CSV processor not initialized")
        
        orders = csv_processor.get_sales_orders_by_model()
        
        if orders.empty:
            return {
                'total_orders': 0,
                'by_model': {},
                'by_customer_type': {},
                'orders': []
            }
        
        return {
            'total_orders': len(orders),
            'by_model': orders.groupby('Scooter_Model')['Quantity'].sum().to_dict(),
            'by_customer_type': orders.groupby('Customer_Type')['Quantity'].sum().to_dict(),
            'orders': orders.to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error getting sales orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'Hugo API',
        'agents_initialized': all([
            analytical_agent is not None,
            reactive_agent is not None,
            optimization_agent is not None,
            bom_service is not None,
            inventory_service is not None,
            csv_processor is not None,
            email_processor is not None
        ])
    }