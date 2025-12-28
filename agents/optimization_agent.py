# agents/optimization_agent.py
from typing import Dict, List, Any
import google.generativeai as genai
import json
import logging

logger = logging.getLogger(__name__)

class OptimizationAgent:
    """Agent for optimizing inventory dispatch parameters"""
    
    def __init__(self, api_key: str, csv_processor, inventory_service):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.csv_processor = csv_processor
        self.inventory_service = inventory_service
    
    async def optimize_inventory_parameters(self, material_id: str = None) -> Dict[str, Any]:
        """Optimize dispatch parameters for materials"""
        
        if material_id:
            # Optimize single material
            optimization = self.inventory_service.optimize_dispatch_parameters(material_id)
            
            # Get AI recommendations
            prompt = self._create_optimization_prompt(optimization)
            
            try:
                response = self.model.generate_content(prompt)
                ai_recommendation = response.text
            except Exception as e:
                logger.error(f"Error generating AI recommendation: {e}")
                ai_recommendation = "Unable to generate AI recommendation at this time."
            
            return {
                'material_id': material_id,
                'optimization': optimization,
                'ai_recommendation': ai_recommendation
            }
        else:
            # Optimize all materials that need optimization
            recommendations = self.inventory_service.get_reorder_recommendations()
            
            optimizations = []
            for rec in recommendations[:10]:  # Top 10
                material_id = rec['material_id']
                opt = self.inventory_service.optimize_dispatch_parameters(material_id)
                optimizations.append(opt)
            
            return {
                'total_materials_analyzed': len(optimizations),
                'optimizations': optimizations
            }
    
    def _create_optimization_prompt(self, optimization: Dict) -> str:
        """Create prompt for AI optimization recommendations"""
        
        prompt = f"""You are Hugo, an AI inventory optimization expert for Voltway electric scooters.

**Material Optimization Analysis:**
{json.dumps(optimization, indent=2, default=str)}

**Your Task:**
Analyze the current vs recommended dispatch parameters and provide:
1. A clear explanation of why these changes are recommended
2. The expected benefits (e.g., reduced stockouts, lower carrying costs)
3. Any risks or considerations
4. Implementation priority (High/Medium/Low)

**Provide a concise, actionable recommendation in 3-4 sentences.**"""

        return prompt
    
    async def suggest_cost_optimization(self) -> Dict[str, Any]:
        """Suggest cost optimization opportunities"""
        
        # Analyze current inventory costs
        inventory_summary = self.inventory_service.get_inventory_summary()
        stock_health = self.inventory_service.analyze_stock_health()
        
        # Identify optimization opportunities
        opportunities = []
        
        # 1. Excess stock opportunities
        for item in stock_health:
            if item['health_status'] == 'HEALTHY' and item['stock_ratio'] > 2.0:
                opportunities.append({
                    'type': 'EXCESS_STOCK',
                    'material_id': item['Material_ID'],
                    'description': item.get('Description', item['Material_ID']),
                    'current_stock': item['Available_Stock'],
                    'recommendation': f"Reduce reorder point to lower carrying costs. Current stock is {item['stock_ratio']:.1f}x the reorder point.",
                    'potential_savings': 'Medium'
                })
        
        # 2. Bulk order opportunities
        reorder_recs = self.inventory_service.get_reorder_recommendations()
        high_volume_materials = [r for r in reorder_recs if r['recommended_order_qty'] > 100]
        
        for item in high_volume_materials:
            opportunities.append({
                'type': 'BULK_ORDER',
                'material_id': item['material_id'],
                'description': item['description'],
                'recommendation': f"Consider negotiating bulk discount for {item['recommended_order_qty']} units",
                'potential_savings': 'High'
            })
        
        # Get AI analysis
        prompt = f"""You are Hugo, a cost optimization expert for Voltway.

**Inventory Summary:**
{json.dumps(inventory_summary, indent=2, default=str)}

**Optimization Opportunities:**
{json.dumps(opportunities[:10], indent=2, default=str)}

**Your Task:**
Provide a prioritized list of the top 3 cost optimization actions Voltway should take, with estimated impact and implementation difficulty."""

        try:
            response = self.model.generate_content(prompt)
            ai_analysis = response.text
        except Exception as e:
            logger.error(f"Error generating cost optimization: {e}")
            ai_analysis = "Unable to generate analysis at this time."
        
        return {
            'opportunities': opportunities,
            'ai_analysis': ai_analysis
        }