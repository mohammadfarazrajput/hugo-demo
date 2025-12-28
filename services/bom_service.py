# services/bom_service.py
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BOMService:
    def __init__(self, csv_processor, pdf_processor):
        self.csv_processor = csv_processor
        self.pdf_processor = pdf_processor
        self.specs = {}
    
    def load_specs(self):
        """Load all scooter specifications"""
        self.specs = self.pdf_processor.parse_all_specs()
        return self.specs
    
    def get_bom_for_model(self, model: str) -> Optional[List[Dict]]:
        """Get BOM for a specific scooter model"""
        if not self.specs:
            self.load_specs()
        
        if model in self.specs:
            return self.specs[model]['bom']
        return None
    
    def calculate_build_capacity(self, model: str) -> Dict:
        """
        Calculate how many scooters of a given model can be built
        based on current stock levels and BOM requirements
        """
        bom = self.get_bom_for_model(model)
        
        if not bom:
            return {
                'scooter_model': model,
                'max_units': 0,
                'bottleneck_materials': [],
                'sufficient_materials': [],
                'error': f'No BOM found for model {model}'
            }
        
        bottleneck_materials = []
        sufficient_materials = []
        min_units = float('inf')
        
        for item in bom:
            material_id = item['material_id']
            required_qty = item['quantity']
            
            # Get current stock
            stock_info = self.csv_processor.get_stock_level(material_id)
            
            if stock_info:
                available = stock_info.get('Available_Stock', 0)
                
                # Calculate how many units can be built with this material
                units_possible = int(available / required_qty) if required_qty > 0 else 0
                
                material_info = self.csv_processor.get_material_info(material_id)
                description = material_info.get('Description', material_id) if material_info else material_id
                
                material_data = {
                    'material_id': material_id,
                    'description': description,
                    'required_per_unit': required_qty,
                    'available_stock': available,
                    'units_possible': units_possible
                }
                
                if units_possible < min_units:
                    min_units = units_possible
                
                if units_possible == 0:
                    bottleneck_materials.append(material_data)
                else:
                    sufficient_materials.append(material_id)
            else:
                # No stock info found - this is a bottleneck
                bottleneck_materials.append({
                    'material_id': material_id,
                    'description': material_id,
                    'required_per_unit': required_qty,
                    'available_stock': 0,
                    'units_possible': 0
                })
                min_units = 0
        
        # If min_units is still infinity, no materials were found
        if min_units == float('inf'):
            min_units = 0
        
        return {
            'scooter_model': model,
            'max_units': int(min_units),
            'bottleneck_materials': bottleneck_materials,
            'sufficient_materials': sufficient_materials
        }
    
    def calculate_material_requirements(self, model: str, quantity: int) -> List[Dict]:
        """
        Calculate material requirements for building X units of a model
        """
        bom = self.get_bom_for_model(model)
        
        if not bom:
            return []
        
        requirements = []
        
        for item in bom:
            material_id = item['material_id']
            required_qty = item['quantity'] * quantity
            
            stock_info = self.csv_processor.get_stock_level(material_id)
            available = stock_info.get('Available_Stock', 0) if stock_info else 0
            
            shortage = max(0, required_qty - available)
            
            material_info = self.csv_processor.get_material_info(material_id)
            description = material_info.get('Description', material_id) if material_info else material_id
            
            requirements.append({
                'material_id': material_id,
                'description': description,
                'required_quantity': required_qty,
                'available_stock': available,
                'shortage': shortage,
                'status': 'sufficient' if shortage == 0 else 'shortage'
            })
        
        return requirements