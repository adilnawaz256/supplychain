"""Wisualyst Machine Learning & Decision Intelligence Algorithms Package.

This package centralizes all mathematical, statistical, machine learning,
and optimization algorithms powering the platform.
"""

from backend.ml.forecasting.engine import StatisticalForecastEngine
from backend.ml.inventory.optimization import InventoryOptimizer
from backend.ml.risk.engine import InventoryRiskEngine
from backend.ml.pricing.engine import PricingOptimizationEngine
from backend.ml.policy.engine import InventoryPolicySimulationEngine
from backend.ml.customer.engine import CustomerLTVSegmentationEngine
from backend.ml.cross_sell.engine import MarketBasketRecommendationEngine
from backend.ml.trade_area.engine import TradeAreaModellingEngine
from backend.ml.assortment.engine import AssortmentOptimizerEngine
from backend.ml.procurement.engine import ProcurementOptimizerEngine

def get_react_agent():
    from backend.ml.agents.react_agent import ReActAgent
    return ReActAgent

def get_multi_agent_workflow():
    from backend.ml.agents.workflow import MultiAgentSupplyChainWorkflow
    return MultiAgentSupplyChainWorkflow

__all__ = [
    "StatisticalForecastEngine",
    "InventoryOptimizer",
    "InventoryRiskEngine",
    "PricingOptimizationEngine",
    "InventoryPolicySimulationEngine",
    "CustomerLTVSegmentationEngine",
    "MarketBasketRecommendationEngine",
    "TradeAreaModellingEngine",
    "AssortmentOptimizerEngine",
    "ProcurementOptimizerEngine",
    "get_react_agent",
    "get_multi_agent_workflow",
]
