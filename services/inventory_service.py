# services/inventory_service.py
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self, csv_processor):
        self.csv_processor = csv_processor
    
    def get_inventory_summary(self) -> Dict:
        """Get overall inventory summary statistics"""
        data = self.csv_processor.data
        
        if 'stock_levels' not in data:
            return {'error': 'Stock levels data not available'}
        
        stock = data['stock_levels']
        
        summary = {
            'total_materials': len(stock),
            'total_stock_value': 0,
            'low_stock_count': len(self.csv_processor.get_low_stock_materials()),
            'out_of_stock_count': len(stock[stock['Available_Stock'] <= 0]),
            'categories': {}
        }
        
        # Calculate total stock value
        if 'materials' in data:
            materials = data['materials']
            merged = stock.merge(materials[['Material_ID', 'Unit_Price', 'Category']], on='Material_ID', how='left')
            merged['stock_value'] = merged['Current_Stock'] * merged['Unit_Price']
            summary['total_stock_value'] = merged['stock_value'].sum()
            
            # Group by category
            category_summary = merged.groupby('Category').agg({
                'Material_ID': 'count',
                'stock_value': 'sum'
            }).reset_index()
            category_summary.columns = ['Category', 'Material_Count', 'Total_Value']
            summary['categories'] = category_summary.to_dict('records')
        
        return summary
    
    def analyze_stock_health(self) -> List[Dict]:
        """Analyze stock health for all materials"""
        stock_levels = self.csv_processor.data.get('stock_levels')
        dispatch_params = self.csv_processor.data.get('dispatch_parameters')
        materials = self.csv_processor.data.get('materials')
        
        if stock_levels is None or dispatch_params is None:
            return []
        
        # Merge data
        merged = stock_levels.merge(dispatch_params, on='Material_ID', how='inner')
        
        if materials is not None:
            merged = merged.merge(
                materials[['Material_ID', 'Description', 'Category']], 
                on='Material_ID', 
                how='left'
            )
        
        # Calculate health metrics
        merged['stock_ratio'] = merged['Available_Stock'] / merged['Reorder_Point']
        merged['days_of_stock'] = self._estimate_days_of_stock(merged)
        
        # Classify health status
        def get_health_status(row):
            ratio = row['stock_ratio']
            if ratio <= 0:
                return 'OUT_OF_STOCK'
            elif ratio < 0.5:
                return 'CRITICAL'
            elif ratio < 1.0:
                return 'LOW'
            elif ratio < 1.5:
                return 'ADEQUATE'
            else:
                return 'HEALTHY'
        
        merged['health_status'] = merged.apply(get_health_status, axis=1)
        
        result = merged[[
            'Material_ID', 'Description', 'Category', 'Available_Stock', 
            'Reorder_Point', 'Safety_Stock', 'stock_ratio', 'days_of_stock', 'health_status'
        ]].to_dict('records')
        
        return result
    
    def _estimate_days_of_stock(self, df: pd.DataFrame) -> pd.Series:
        """Estimate days of stock remaining based on historical usage"""
        # Simplified estimation - in reality, you'd calculate based on stock_movements
        # For now, we'll use a simple heuristic
        stock_movements = self.csv_processor.data.get('stock_movements')
        
        if stock_movements is None:
            return pd.Series([30] * len(df))  # Default to 30 days
        
        # Calculate average daily consumption per material
        movements = stock_movements[stock_movements['Movement_Type'] == 'Consumption'].copy()
        if movements.empty:
            return pd.Series([30] * len(df))
        
        movements['Date'] = pd.to_datetime(movements['Date'])
        date_range = (movements['Date'].max() - movements['Date'].min()).days or 1
        
        daily_consumption = movements.groupby('Material_ID')['Quantity'].sum() / date_range
        
        # Merge with current stock
        days_estimate = []
        for _, row in df.iterrows():
            material_id = row['Material_ID']
            available = row['Available_Stock']
            
            if material_id in daily_consumption.index:
                daily_use = daily_consumption[material_id]
                if daily_use > 0:
                    days = available / daily_use
                    days_estimate.append(min(days, 365))  # Cap at 1 year
                else:
                    days_estimate.append(365)
            else:
                days_estimate.append(30)  # Default
        
        return pd.Series(days_estimate)
    
    def get_reorder_recommendations(self) -> List[Dict]:
        """Get materials that should be reordered"""
        low_stock = self.csv_processor.get_low_stock_materials(threshold=1.0)
        
        recommendations = []
        
        for item in low_stock:
            material_id = item['Material_ID']
            
            # Get pending orders
            pending = self.csv_processor.get_pending_orders(material_id)
            pending_qty = pending['Quantity'].sum() if not pending.empty else 0
            
            # Calculate recommended order quantity
            reorder_point = item.get('Reorder_Point', 0)
            safety_stock = item.get('Safety_Stock', 0)
            lot_size = item.get('Lot_Size', 1)
            available = item.get('Available_Stock', 0)
            
            # Calculate shortage
            target_stock = reorder_point + safety_stock
            shortage = max(0, target_stock - available - pending_qty)
            
            # Round up to nearest lot size
            order_qty = ((shortage // lot_size) + (1 if shortage % lot_size > 0 else 0)) * lot_size
            
            if order_qty > 0:
                recommendations.append({
                    'material_id': material_id,
                    'description': item.get('Description', material_id),
                    'category': item.get('Category', 'Unknown'),
                    'current_stock': available,
                    'pending_orders': pending_qty,
                    'reorder_point': reorder_point,
                    'recommended_order_qty': order_qty,
                    'priority': 'HIGH' if available < reorder_point * 0.5 else 'MEDIUM'
                })
        
        return recommendations
    
    def forecast_stockout_risk(self, days_ahead: int = 30) -> List[Dict]:
        """Forecast materials at risk of stockout in the next X days"""
        health = self.analyze_stock_health()
        
        at_risk = []
        
        for item in health:
            days_of_stock = item.get('days_of_stock', 30)
            
            if days_of_stock < days_ahead:
                at_risk.append({
                    'material_id': item['Material_ID'],
                    'description': item.get('Description', item['Material_ID']),
                    'days_until_stockout': round(days_of_stock, 1),
                    'current_stock': item['Available_Stock'],
                    'health_status': item['health_status'],
                    'urgency': 'CRITICAL' if days_of_stock < 7 else 'HIGH' if days_of_stock < 14 else 'MEDIUM'
                })
        
        # Sort by urgency
        at_risk.sort(key=lambda x: x['days_until_stockout'])
        
        return at_risk
    
    def optimize_dispatch_parameters(self, material_id: str) -> Dict:
        """Suggest optimized dispatch parameters for a material"""
        # Get historical data
        movements = self.csv_processor.data.get('stock_movements')
        current_params = self.csv_processor.get_dispatch_parameters(material_id)
        
        if movements is None or current_params is None:
            return {'error': 'Insufficient data for optimization'}
        
        # Filter movements for this material
        mat_movements = movements[movements['Material_ID'] == material_id].copy()
        
        if mat_movements.empty:
            return {'error': 'No movement history for this material'}
        
        # Calculate consumption patterns
        consumption = mat_movements[mat_movements['Movement_Type'] == 'Consumption']
        
        if consumption.empty:
            return current_params
        
        consumption['Date'] = pd.to_datetime(consumption['Date'])
        date_range = (consumption['Date'].max() - consumption['Date'].min()).days or 1
        
        # Calculate average daily consumption
        total_consumption = consumption['Quantity'].sum()
        avg_daily_consumption = total_consumption / date_range
        
        # Get supplier lead time
        material_info = self.csv_processor.get_material_info(material_id)
        orders = self.csv_processor.get_pending_orders(material_id)
        
        # Estimate lead time from orders (simplified)
        lead_time_days = 14  # Default
        
        if not orders.empty and 'Expected_Delivery' in orders.columns and 'Order_Date' in orders.columns:
            try:
                orders['Lead_Time'] = (
                    pd.to_datetime(orders['Expected_Delivery']) - 
                    pd.to_datetime(orders['Order_Date'])
                ).dt.days
                lead_time_days = orders['Lead_Time'].mean()
            except:
                pass
        
        # Calculate optimal parameters
        # Safety stock = avg_daily_consumption * lead_time * safety_factor
        safety_factor = 1.5  # 50% buffer
        optimal_safety_stock = avg_daily_consumption * lead_time_days * safety_factor
        
        # Reorder point = (avg_daily_consumption * lead_time) + safety_stock
        optimal_reorder_point = (avg_daily_consumption * lead_time_days) + optimal_safety_stock
        
        # Lot size - optimize for ordering frequency (e.g., every 2 weeks)
        order_frequency_days = 14
        optimal_lot_size = avg_daily_consumption * order_frequency_days
        
        # Round to reasonable values
        optimal_safety_stock = round(optimal_safety_stock, 2)
        optimal_reorder_point = round(optimal_reorder_point, 2)
        optimal_lot_size = round(optimal_lot_size, 2)
        
        return {
            'material_id': material_id,
            'current_parameters': current_params,
            'recommended_parameters': {
                'Reorder_Point': optimal_reorder_point,
                'Safety_Stock': optimal_safety_stock,
                'Lot_Size': optimal_lot_size,
            },
            'analysis': {
                'avg_daily_consumption': round(avg_daily_consumption, 2),
                'estimated_lead_time_days': round(lead_time_days, 1),
                'data_period_days': date_range
            }
        }