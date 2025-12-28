# agents/reactive_agent.py
from typing import List, Dict, Any
from datetime import datetime
import logging
import pandas as pd  # <--- FIX 1: Missing import added

logger = logging.getLogger(__name__)

class ReactiveAgent:
    """Agent for monitoring and generating alerts"""
    
    def __init__(self, csv_processor, email_processor, bom_service, inventory_service):
        self.csv_processor = csv_processor
        self.email_processor = email_processor
        self.bom_service = bom_service
        self.inventory_service = inventory_service
    
    def generate_alerts(self) -> List[Dict[str, Any]]:
        alerts = []
        alerts.extend(self._check_stock_alerts())
        alerts.extend(self._check_email_alerts())
        alerts.extend(self._check_order_alerts())
        alerts.extend(self._check_capacity_alerts())
        
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 4))
        return alerts

    def _check_stock_alerts(self) -> List[Dict]:
        alerts = []
        low_stock = self.csv_processor.get_low_stock_materials(threshold=0.5)
        for item in low_stock:
            alerts.append({
                'alert_type': 'LOW_STOCK',
                'severity': 'critical' if item.get('Available_Stock', 0) == 0 else 'high',
                'message': f"Critical: {item.get('Description', item['Material_ID'])} is at {item.get('Available_Stock', 0)} units",
                'material_id': item['Material_ID'],
                'action_required': f"Reorder immediately. Lot size: {item.get('Lot_Size', 'N/A')}",
                'created_at': datetime.now().isoformat()
            })
        
        risks = self.inventory_service.forecast_stockout_risk(14)
        for risk in risks[:5]:
            if risk['urgency'] in ['CRITICAL', 'HIGH']:
                alerts.append({
                    'alert_type': 'STOCKOUT_RISK',
                    'severity': 'high' if risk['urgency'] == 'CRITICAL' else 'medium',
                    'message': f"{risk['description']} out in {risk['days_until_stockout']} days",
                    'material_id': risk['material_id'],
                    'action_required': "Expedite delivery with supplier",
                    'created_at': datetime.now().isoformat()
                })
        return alerts

    def _check_email_alerts(self) -> List[Dict]:
        alerts = []
        emails = self.email_processor.parse_all_emails()
        critical_emails = self.email_processor.get_critical_emails(emails)
        
        for email in critical_emails:
            severity = 'critical' if email['email_type'] in ['Urgent Alert', 'Order Cancellation'] else 'high'
            extracted = email.get('extracted_info', {})
            alerts.append({
                'alert_type': 'SUPPLIER_ALERT',
                'severity': severity,
                'message': f"{email['email_type']}: {email['subject']}",
                'material_id': extracted.get('material_ids', [None])[0],
                'order_id': extracted.get('order_numbers', [None])[0],
                'action_required': f"Review email source: {email['filename']}",
                'created_at': datetime.now().isoformat(),
                'details': {'sender': email['sender'], 'extracted_info': extracted}
            })
        return alerts

    def _check_order_alerts(self) -> List[Dict]:
        alerts = []
        # FIX 2: Create a copy to avoid SettingWithCopyWarning
        pending_orders = self.csv_processor.get_pending_orders().copy()
        
        if pending_orders.empty or 'Expected_Delivery' not in pending_orders.columns:
            return alerts
        
        try:
            pending_orders['Expected_Delivery'] = pd.to_datetime(pending_orders['Expected_Delivery'])
            today = pd.Timestamp.now().normalize() # Use normalize to compare dates only
            overdue = pending_orders[pending_orders['Expected_Delivery'] < today]
            
            for _, order in overdue.iterrows():
                alerts.append({
                    'alert_type': 'OVERDUE_ORDER',
                    'severity': 'high',
                    'message': f"Order {order['Order_ID']} for {order['Material_ID']} is overdue",
                    'material_id': order['Material_ID'],
                    'order_id': order['Order_ID'],
                    'action_required': f"Contact supplier {order.get('Supplier_ID', 'N/A')} for status",
                    'created_at': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error checking overdue orders: {e}")
        return alerts

    def _check_capacity_alerts(self) -> List[Dict]:
        alerts = []
        # FIX 3: Get dynamic list of models from BOM service instead of hardcoding
        try:
            # Check if your BOM service has the specs loaded
            available_models = list(self.bom_service.specs.keys())
            if not available_models:
                # Fallback to hardcoded only if dynamic loading fails
                available_models = ['S1_V1', 'S1_V2', 'S2_V1', 'S2_V2', 'S3_V1', 'S3_V2']
        except:
            available_models = ['S1_V1', 'S1_V2', 'S2_V1', 'S2_V2', 'S3_V1', 'S3_V2']
        
        for model in available_models:
            capacity = self.bom_service.calculate_build_capacity(model)
            max_units = capacity.get('max_units', 0)
            
            if max_units < 10:
                severity = 'critical' if max_units == 0 else 'high'
                alerts.append({
                    'alert_type': 'LOW_BUILD_CAPACITY',
                    'severity': severity,
                    'message': f"Build capacity for {model} is critically low ({max_units} units left)",
                    'action_required': f"Review bottlenecks: {', '.join([m['material_id'] for m in capacity.get('bottleneck_materials', [])[:2]])}",
                    'created_at': datetime.now().isoformat(),
                    'details': capacity
                })
        return alerts

    def get_alert_summary(self) -> Dict[str, Any]:
        alerts = self.generate_alerts()
        summary = {
            'total_alerts': len(alerts),
            'by_severity': {
                'critical': len([a for a in alerts if a['severity'] == 'critical']),
                'high': len([a for a in alerts if a['severity'] == 'high']),
                'medium': len([a for a in alerts if a['severity'] == 'medium']),
                'low': len([a for a in alerts if a['severity'] == 'low'])
            },
            'by_type': {},
            'alerts': alerts
        }
        for alert in alerts:
            t = alert['alert_type']
            summary['by_type'][t] = summary['by_type'].get(t, 0) + 1
        return summary