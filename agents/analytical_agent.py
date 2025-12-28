# agents/analytical_agent.py
import json
from typing import Dict, Any
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class AnalyticalAgent:
    """Agent for answering analytical questions about operations"""
    
    def __init__(self, api_key: str, csv_processor, bom_service, inventory_service):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.csv_processor = csv_processor
        self.bom_service = bom_service
        self.inventory_service = inventory_service
    
    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer analytical questions using AI and data"""
        
        # Gather relevant context based on question
        context = self._gather_context(question)
        
        # Create prompt for Gemini
        prompt = self._create_prompt(question, context)
        
        # Get AI response
        try:
            response = self.model.generate_content(prompt)
            answer = response.text
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            answer = "I encountered an error processing your question. Please try rephrasing it."
        
        return {
            'answer': answer,
            'data': context,
            'question': question
        }
    
    def _gather_context(self, question: str) -> Dict[str, Any]:
        """Gather relevant data based on the question"""
        context = {}
        question_lower = question.lower()
        
        # Build capacity questions
        if any(word in question_lower for word in ['build', 'capacity', 'produce', 'manufacture', 'make']):
            # Check if specific model mentioned
            models = ['s1_v1', 's1_v2', 's2_v1', 's2_v2', 's3_v1', 's3_v2']
            for model in models:
                if model.replace('_', ' ') in question_lower or model in question_lower:
                    context['build_capacity'] = self.bom_service.calculate_build_capacity(model.upper())
                    break
            
            # If no specific model, get capacity for all models
            if 'build_capacity' not in context:
                context['all_capacities'] = {}
                for model in models:
                    capacity = self.bom_service.calculate_build_capacity(model.upper())
                    context['all_capacities'][model] = capacity
        
        # Stock/inventory questions
        if any(word in question_lower for word in ['stock', 'inventory', 'low', 'running', 'shortage']):
            context['low_stock_materials'] = self.csv_processor.get_low_stock_materials()
            context['inventory_summary'] = self.inventory_service.get_inventory_summary()
            context['reorder_recommendations'] = self.inventory_service.get_reorder_recommendations()
        
        # Supplier questions
        if any(word in question_lower for word in ['supplier', 'vendor', 'delivery', 'lead time']):
            context['supplier_performance'] = self.csv_processor.get_supplier_performance()
        
        # Order questions
        if any(word in question_lower for word in ['order', 'orders', 'pending']):
            all_orders = self.csv_processor.get_pending_orders()
            context['pending_orders'] = {
                'count': len(all_orders),
                'total_value': all_orders['Total_Price'].sum() if not all_orders.empty else 0,
                'orders': all_orders.head(10).to_dict('records') if not all_orders.empty else []
            }
        
        # Sales questions
        if any(word in question_lower for word in ['sales', 'customer', 'demand', 'webshop', 'fleet']):
            sales_orders = self.csv_processor.get_sales_orders_by_model()
            if not sales_orders.empty:
                context['sales_summary'] = {
                    'total_orders': len(sales_orders),
                    'by_model': sales_orders.groupby('Scooter_Model')['Quantity'].sum().to_dict(),
                    'by_customer_type': sales_orders.groupby('Customer_Type')['Quantity'].sum().to_dict(),
                    'recent_orders': sales_orders.head(10).to_dict('records')
                }
        
        # Risk/bottleneck questions
        if any(word in question_lower for word in ['risk', 'bottleneck', 'problem', 'issue', 'concern']):
            context['stockout_risks'] = self.inventory_service.forecast_stockout_risk(30)
            context['stock_health'] = self.inventory_service.analyze_stock_health()[:10]
        
        # Price/cost questions
        if any(word in question_lower for word in ['price', 'cost', 'expensive', 'cheap']):
            materials = self.csv_processor.data.get('materials')
            if materials is not None:
                sorted_materials = materials.sort_values('Unit_Price', ascending=False)
                context['price_analysis'] = {
                    'most_expensive': sorted_materials.head(10).to_dict('records'),
                    'least_expensive': sorted_materials.tail(10).to_dict('records')
                }
        
        return context
    
    def _create_prompt(self, question: str, context: Dict) -> str:
        """Create a detailed prompt for the AI"""
        
        prompt = f"""You are Hugo, an intelligent AI procurement assistant for Voltway, an electric scooter manufacturing company.

**User Question:** {question}

**Available Data Context:**
{json.dumps(context, indent=2, default=str)}

**Your Task:**
1. Analyze the provided data carefully
2. Answer the user's question directly and clearly
3. Provide specific numbers, metrics, and insights from the data
4. Highlight any risks, bottlenecks, or concerns
5. Recommend actionable next steps if relevant

**Response Guidelines:**
- Be specific and use actual data from the context
- If data is missing, acknowledge it
- Focus on actionable insights
- Use clear formatting with bullet points when listing multiple items
- If there are critical issues, emphasize them

**Answer:**"""

        return prompt