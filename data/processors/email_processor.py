# data/processors/email_processor.py
import email
from email import policy
from pathlib import Path
from typing import List, Dict, Optional
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self, email_dir: str):
        self.email_dir = Path(email_dir)
        
    def parse_all_emails(self) -> List[Dict]:
        """Parse all email files in the directory"""
        logger.info("📧 Parsing supplier emails...")
        
        emails = []
        
        if not self.email_dir.exists():
            logger.warning(f"  ⚠️  Email directory not found: {self.email_dir}")
            return emails
        
        # Support both .eml and .msg formats
        email_files = list(self.email_dir.glob('*.eml')) + list(self.email_dir.glob('*.msg'))
        
        # If no .eml/.msg files, try reading as text files
        if not email_files:
            email_files = list(self.email_dir.glob('email_*'))
        
        for email_file in email_files:
            parsed = self.parse_email(email_file)
            if parsed:
                emails.append(parsed)
        
        logger.info(f"  ✅ Parsed {len(emails)} emails")
        return emails
    
    def parse_email(self, email_path: Path) -> Optional[Dict]:
        """Parse a single email file"""
        try:
            # Try parsing as EML first
            if email_path.suffix == '.eml':
                return self._parse_eml(email_path)
            else:
                # Parse as plain text
                return self._parse_text_email(email_path)
                
        except Exception as e:
            logger.error(f"  ⚠️  Error parsing {email_path.name}: {e}")
            return None
    
    def _parse_eml(self, email_path: Path) -> Optional[Dict]:
        """Parse .eml formatted email"""
        with open(email_path, 'r', encoding='utf-8', errors='ignore') as f:
            msg = email.message_from_file(f, policy=policy.default)
        
        body = self._get_body(msg)
        subject = str(msg.get('subject', ''))
        
        email_data = {
            'filename': email_path.name,
            'subject': subject,
            'sender': str(msg.get('from', '')),
            'date': str(msg.get('date', '')),
            'body': body,
            'email_type': self._classify_email(email_path.name, subject),
        }
        
        # Extract structured information
        email_data['extracted_info'] = self._extract_info(email_data)
        
        return email_data
    
    def _parse_text_email(self, email_path: Path) -> Optional[Dict]:
        """Parse plain text email file"""
        with open(email_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract subject from filename or content
        filename = email_path.name
        subject = self._extract_subject_from_filename(filename)
        
        email_data = {
            'filename': filename,
            'subject': subject,
            'sender': 'Unknown',
            'date': 'Unknown',
            'body': content,
            'email_type': self._classify_email(filename, subject),
        }
        
        email_data['extracted_info'] = self._extract_info(email_data)
        
        return email_data
    
    def _get_body(self, msg) -> str:
        """Extract email body from email message"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        return str(part.get_payload())
        else:
            try:
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                return str(msg.get_payload())
        return ""
    
    def _extract_subject_from_filename(self, filename: str) -> str:
        """Extract subject from filename"""
        # Remove extension and common prefixes
        subject = filename.replace('.eml', '').replace('.msg', '').replace('email_', '')
        # Replace underscores with spaces and clean up
        subject = subject.replace('_', ' ')
        return subject.title()
    
    def _classify_email(self, filename: str, subject: str) -> str:
        """Classify email type"""
        text = (filename + ' ' + subject).lower()
        
        if 'delay' in text:
            return 'Delivery Delay'
        elif 'price' in text or 'discount' in text:
            return 'Price Update'
        elif 'cancel' in text:
            return 'Order Cancellation'
        elif 'urgent' in text or 'quality' in text or 'alert' in text:
            return 'Urgent Alert'
        elif 'shipment' in text or 'partial' in text:
            return 'Shipment Update'
        elif 'amendment' in text or 'proposal' in text:
            return 'Contract Amendment'
        elif 'discontinu' in text:
            return 'Product Discontinuation'
        else:
            return 'General Communication'
    
    def _extract_info(self, email_data: Dict) -> Dict:
        """Extract structured information from email"""
        body = email_data['body']
        email_type = email_data['email_type']
        
        info = {}
        
        # Extract order numbers (O5007, OS045, O5021, etc.)
        order_pattern = r'\bO[S]?\d+\b'
        orders = re.findall(order_pattern, body)
        if orders:
            info['order_numbers'] = list(set(orders))
        
        # Extract material IDs (various formats)
        material_patterns = [
            r'\b[A-Z]_[A-Z0-9]+_[A-Z0-9]+\b',  # M_48V_1000W format
            r'\bS\d_V\d\b'  # S1_V1, S2_V2 format
        ]
        materials = []
        for pattern in material_patterns:
            materials.extend(re.findall(pattern, body))
        if materials:
            info['material_ids'] = list(set(materials))
        
        # Extract dates (multiple formats)
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
        ]
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, body, re.IGNORECASE))
        if dates:
            info['dates'] = dates
        
        # Extract prices and monetary values
        price_patterns = [
            r'\$\s?[\d,]+\.?\d*',
            r'₹\s?[\d,]+\.?\d*',
            r'€\s?[\d,]+\.?\d*',
            r'[\d,]+\.?\d*\s?(?:USD|EUR|INR|Rs)'
        ]
        prices = []
        for pattern in price_patterns:
            prices.extend(re.findall(pattern, body, re.IGNORECASE))
        if prices:
            info['prices'] = prices
        
        # Extract percentages
        percent_pattern = r'\b(\d+\.?\d*)\s?%'
        percentages = re.findall(percent_pattern, body)
        if percentages:
            info['percentages'] = [f"{p}%" for p in percentages]
        
        # Extract quantities
        qty_pattern = r'(?:quantity|qty)[\s:]+(\d+)'
        quantities = re.findall(qty_pattern, body, re.IGNORECASE)
        if quantities:
            info['quantities'] = quantities
        
        # Type-specific extraction
        if 'delay' in email_type.lower():
            delay_pattern = r'(\d+)\s*(day|week|month)s?'
            delays = re.findall(delay_pattern, body, re.IGNORECASE)
            if delays:
                info['delay_duration'] = f"{delays[0][0]} {delays[0][1]}s"
        
        return info
    
    def get_emails_by_type(self, emails: List[Dict], email_type: str) -> List[Dict]:
        """Filter emails by type"""
        return [e for e in emails if email_type.lower() in e['email_type'].lower()]
    
    def get_critical_emails(self, emails: List[Dict]) -> List[Dict]:
        """Get urgent/critical emails"""
        critical_types = ['Urgent Alert', 'Order Cancellation', 'Delivery Delay', 'Quality Issue']
        return [e for e in emails if e['email_type'] in critical_types]