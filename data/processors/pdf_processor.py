# data/processors/pdf_processor.py
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, specs_dir: str):
        self.specs_dir = Path(specs_dir)
        
    def parse_all_specs(self) -> Dict[str, Dict]:
        """Parse all PDF specification files"""
        logger.info("📄 Parsing scooter specifications...")
        
        specs = {}
        
        if not self.specs_dir.exists():
            logger.warning(f"  ⚠️  Specs directory not found: {self.specs_dir}")
            return specs
        
        pdf_files = list(self.specs_dir.glob('*.pdf'))
        
        for pdf_file in pdf_files:
            # Extract model name from filename
            # e.g., "scanned_S1_V1_specs.pdf" -> "S1_V1"
            model_name = pdf_file.stem.replace('scanned_', '').replace('_specs', '')
            
            spec_data = self.parse_spec(pdf_file, model_name)
            if spec_data:
                specs[model_name] = spec_data
        
        logger.info(f"  ✅ Parsed {len(specs)} specification files")
        return specs
    
    def parse_spec(self, pdf_path: Path, model_name: str) -> Optional[Dict]:
        """Parse a single PDF specification file"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Extract Bill of Materials
            bom = self._extract_bom(text)
            
            # Extract specifications
            specifications = self._extract_specifications(text)
            
            return {
                'model': model_name,
                'bom': bom,
                'specifications': specifications,
                'raw_text': text[:1000]  # Keep first 1000 chars for debugging
            }
            
        except Exception as e:
            logger.error(f"  ⚠️  Error parsing {pdf_path.name}: {e}")
            return None
    
    def _extract_bom(self, text: str) -> List[Dict]:
        """Extract Bill of Materials from specification text"""
        bom = []
        
        # Common patterns for BOM entries
        patterns = [
            # Pattern: Material_ID x Quantity or Material_ID: Quantity
            r'([A-Z]_[A-Z0-9_]+)\s*[x:×]\s*(\d+)',
            # Pattern: Quantity x Material_ID
            r'(\d+)\s*[x:×]\s*([A-Z]_[A-Z0-9_]+)',
            # Pattern: Material_ID (Quantity)
            r'([A-Z]_[A-Z0-9_]+)\s*\((\d+)\)',
        ]
        
        seen_materials = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Determine which group is material ID and which is quantity
                if match[0].replace('_', '').replace('-', '').isalnum() and not match[0].isdigit():
                    material_id = match[0]
                    try:
                        quantity = int(match[1])
                    except:
                        continue
                else:
                    material_id = match[1]
                    try:
                        quantity = int(match[0])
                    except:
                        continue
                
                # Avoid duplicates
                if material_id not in seen_materials and len(material_id) > 2:
                    seen_materials.add(material_id)
                    bom.append({
                        'material_id': material_id,
                        'quantity': quantity
                    })
        
        return bom
    
    def _extract_specifications(self, text: str) -> Dict:
        """Extract general specifications from text"""
        specs = {}
        
        # Extract battery capacity
        battery_pattern = r'(\d+)V\s*(\d+)Ah'
        battery_match = re.search(battery_pattern, text)
        if battery_match:
            specs['battery_voltage'] = f"{battery_match.group(1)}V"
            specs['battery_capacity'] = f"{battery_match.group(2)}Ah"
        
        # Extract motor power
        motor_pattern = r'(\d+)W'
        motor_match = re.search(motor_pattern, text)
        if motor_match:
            specs['motor_power'] = f"{motor_match.group(1)}W"
        
        # Extract weight
        weight_pattern = r'(\d+\.?\d*)\s*kg'
        weight_match = re.search(weight_pattern, text, re.IGNORECASE)
        if weight_match:
            specs['weight'] = f"{weight_match.group(1)}kg"
        
        # Extract speed
        speed_pattern = r'(\d+)\s*km/h'
        speed_match = re.search(speed_pattern, text, re.IGNORECASE)
        if speed_match:
            specs['max_speed'] = f"{speed_match.group(1)}km/h"
        
        return specs
    
    def get_bom_for_model(self, specs: Dict[str, Dict], model: str) -> Optional[List[Dict]]:
        """Get BOM for a specific scooter model"""
        if model in specs:
            return specs[model]['bom']
        return None