# data/processors/csv_processor.py
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVProcessor:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data: Dict[str, pd.DataFrame] = {}
        
    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV files into pandas DataFrames"""
        logger.info("📊 Loading CSV data...")
        
        csv_files = {
            'materials': 'material_master.csv',
            'stock_levels': 'stock_levels.csv',
            'material_orders': 'material_orders.csv',
            'sales_orders': 'sales_orders.csv',
            'suppliers': 'suppliers.csv',
            'stock_movements': 'stock_movements.csv',
            'dispatch_parameters': 'dispatch_parameters.csv'
        }
        
        for key, filename in csv_files.items():
            filepath = self.data_dir / filename
            if filepath.exists():
                try:
                    self.data[key] = pd.read_csv(filepath)
                    logger.info(f"  ✅ Loaded {key}: {len(self.data[key])} rows")
                except Exception as e:
                    logger.error(f"  ❌ Error loading {filename}: {e}")
            else:
                logger.warning(f"  ⚠️  Missing {filename}")
        
        return self.data
    
    def get_material_info(self, material_id: str) -> Optional[Dict]:
        """Get detailed information about a material"""
        if 'materials' not in self.data:
            return None
            
        material = self.data['materials'][
            self.data['materials']['Material_ID'] == material_id
        ]
        
        if material.empty:
            return None
            
        return material.iloc[0].to_dict()
    
    def get_stock_level(self, material_id: str) -> Optional[Dict]:
        """Get current stock level for a material"""
        if 'stock_levels' not in self.data:
            return None
            
        stock = self.data['stock_levels'][
            self.data['stock_levels']['Material_ID'] == material_id
        ]
        
        if stock.empty:
            return {'Material_ID': material_id, 'Current_Stock': 0, 'Available_Stock': 0}
            
        return stock.iloc[0].to_dict()
    
    def get_pending_orders(self, material_id: Optional[str] = None) -> pd.DataFrame:
        """Get pending material orders"""
        if 'material_orders' not in self.data:
            return pd.DataFrame()
            
        orders = self.data['material_orders']
        pending = orders[orders['Status'].isin(['Open', 'Pending', 'In Transit'])]
        
        if material_id:
            pending = pending[pending['Material_ID'] == material_id]
            
        return pending
    
    def get_low_stock_materials(self, threshold: float = 1.0) -> List[Dict]:
        """
        Find materials where current stock is below reorder point
        threshold: multiplier for reorder point (1.0 = at reorder point, 0.5 = half of reorder point)
        """
        if 'stock_levels' not in self.data or 'dispatch_parameters' not in self.data:
            return []
            
        stock = self.data['stock_levels'].copy()
        dispatch = self.data['dispatch_parameters'].copy()
        
        # Merge stock with dispatch parameters
        merged = stock.merge(dispatch, on='Material_ID', how='inner')
        
        # Calculate stock ratio
        merged['stock_ratio'] = merged['Available_Stock'] / merged['Reorder_Point']
        
        # Find materials below threshold
        low_stock = merged[merged['stock_ratio'] < threshold].copy()
        
        # Add material descriptions
        if 'materials' in self.data:
            low_stock = low_stock.merge(
                self.data['materials'][['Material_ID', 'Description', 'Category']],
                on='Material_ID',
                how='left'
            )
        
        return low_stock.to_dict('records')
    
    def get_sales_orders_by_model(self, scooter_model: Optional[str] = None, status: Optional[str] = None) -> pd.DataFrame:
        """Get sales orders, optionally filtered by scooter model and status"""
        if 'sales_orders' not in self.data:
            return pd.DataFrame()
            
        orders = self.data['sales_orders'].copy()
        
        if scooter_model:
            orders = orders[orders['Scooter_Model'] == scooter_model]
        
        if status:
            orders = orders[orders['Status'] == status]
            
        return orders
    
    def get_supplier_info(self, supplier_id: str) -> Optional[Dict]:
        """Get supplier information"""
        if 'suppliers' not in self.data:
            return None
            
        supplier = self.data['suppliers'][
            self.data['suppliers']['Supplier_ID'] == supplier_id
        ]
        
        if supplier.empty:
            return None
            
        return supplier.iloc[0].to_dict()
    
    def get_materials_by_category(self, category: str) -> pd.DataFrame:
        """Get all materials in a specific category"""
        if 'materials' not in self.data:
            return pd.DataFrame()
            
        return self.data['materials'][
            self.data['materials']['Category'] == category
        ]
    
    def get_supplier_performance(self) -> List[Dict]:
        """Analyze supplier performance based on orders"""
        if 'material_orders' not in self.data or 'suppliers' not in self.data:
            return []
        
        orders = self.data['material_orders'].copy()
        suppliers = self.data['suppliers'].copy()
        
        # Convert dates
        orders['Order_Date'] = pd.to_datetime(orders['Order_Date'])
        orders['Expected_Delivery'] = pd.to_datetime(orders['Expected_Delivery'])
        
        # Group by supplier
        supplier_stats = orders.groupby('Supplier_ID').agg({
            'Order_ID': 'count',
            'Status': lambda x: (x == 'Delivered').sum(),
            'Total_Price': 'sum'
        }).reset_index()
        
        supplier_stats.columns = ['Supplier_ID', 'Total_Orders', 'Delivered_Orders', 'Total_Spent']
        supplier_stats['On_Time_Rate'] = (supplier_stats['Delivered_Orders'] / supplier_stats['Total_Orders'] * 100).round(2)
        
        # Merge with supplier info
        result = supplier_stats.merge(suppliers, on='Supplier_ID', how='left')
        
        return result.to_dict('records')
    
    def get_dispatch_parameters(self, material_id: str) -> Optional[Dict]:
        """Get dispatch parameters for a material"""
        if 'dispatch_parameters' not in self.data:
            return None
        
        params = self.data['dispatch_parameters'][
            self.data['dispatch_parameters']['Material_ID'] == material_id
        ]
        
        if params.empty:
            return None
        
        return params.iloc[0].to_dict()