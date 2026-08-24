from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import csv
import io
from sqlalchemy.orm import Session
from ai.risk.engine import InventoryRiskEngine

class BaseBIAdapter(ABC):
    @abstractmethod
    def export_inventory_metrics(self, db: Session) -> Any:
        pass

    @abstractmethod
    def export_forecast_dataset(self, db: Session) -> Any:
        pass

class LocalBIAdapter(BaseBIAdapter):
    """
    Standard Local BI Adapter that formats operational supply chain metrics into
    flattened tabular JSON / CSV streams for consumption by PowerBI, Tableau, or Metabase.
    """
    def export_inventory_metrics(self, db: Session) -> Dict[str, Any]:
        risk_engine = InventoryRiskEngine(db)
        risks = risk_engine.get_all_inventory_risks()
        
        # Flatten for BI dataset
        dataset = []
        for r in risks:
            dataset.append({
                "SKU": r["sku"],
                "ProductName": r["product_name"],
                "Warehouse": r["warehouse_name"],
                "CurrentStock": r["current_stock"],
                "AvailableStock": r["available_stock"],
                "AvgDailyDemand": r["avg_daily_demand"],
                "Forecast7dDemand": r["forecast_7d_demand"],
                "DaysOfInventory": r["days_of_inventory"],
                "RiskLevel": r["stockout_risk_level"],
                "RecommendedOrder": r["recommended_order_quantity"],
                "Supplier": r["supplier_name"]
            })

        return {
            "bi_tool": "PowerBI / Tableau Connector",
            "dataset_name": "SupplyChain_Inventory_Risk",
            "record_count": len(dataset),
            "data": dataset
        }

    def export_inventory_metrics_csv(self, db: Session) -> str:
        data = self.export_inventory_metrics(db)["data"]
        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def export_forecast_dataset(self, db: Session) -> Dict[str, Any]:
        # Place-holder interface method for BI time-series datasets
        return {
            "bi_tool": "PowerBI / Tableau Connector",
            "dataset_name": "SupplyChain_Forecast_TimeSeries",
            "record_count": 0,
            "data": []
        }
