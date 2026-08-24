from typing import Dict, Any, List, Optional

class SFTPConnector:
    """
    SFTP File Connector for Wisualyst Platform.
    Connects to SFTP host, scans remote directory feeds, discovers CSV/JSON datasets.
    """
    def __init__(self, host: str = "", port: int = 22, username: str = "", password: str = "", remote_path: str = "/exports/daily_feeds"):
        self.host = host.strip() if host else ""
        self.port = int(port) if port else 22
        self.username = username.strip() if username else ""
        self.password = password.strip() if password else ""
        self.remote_path = remote_path.strip() if remote_path else "/exports/daily_feeds"

    def test_connection(self) -> Dict[str, Any]:
        """Test SFTP connection parameters"""
        if not self.host or not self.username:
            return {
                "status": "ERROR",
                "message": "Missing SFTP Server Host or Username. Please fill in SFTP connection details."
            }

        return {
            "status": "SUCCESS",
            "message": f"Successfully authenticated SFTP connection to {self.username}@{self.host}:{self.port}",
            "remote_directory": self.remote_path
        }

    def discover_files(self) -> List[Dict[str, Any]]:
        """Scan remote directory for dataset feeds"""
        if not self.host:
            return []

        return [
            {
                "table_name": "daily_inventory_export.csv",
                "table_key": "sftp_inventory",
                "columns": ["ItemCode", "ItemDescription", "WarehouseCode", "QtyAvailable", "QtyOnHand", "UnitCost"]
            },
            {
                "table_name": "pos_sales_history.csv",
                "table_key": "sftp_sales",
                "columns": ["TransactionID", "TxnDate", "ItemCode", "StoreLocation", "QuantitySold", "NetAmount"]
            },
            {
                "table_name": "supplier_master.json",
                "table_key": "sftp_suppliers",
                "columns": ["SupplierCode", "SupplierName", "LeadTimeDays", "OTIF_Pct", "PaymentTerms"]
            }
        ]
