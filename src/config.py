"""
Configuration module for the MCA Timetable Intelligent Assistant.
All sensitive values are read from environment variables.
Never hardcode credentials, tokens, or personal paths.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Central configuration loaded from environment variables."""
    # Databricks connection
    databricks_host: str = os.getenv("DATABRICKS_HOST", "")
    databricks_token: str = os.getenv("DATABRICKS_TOKEN", "")
    warehouse_id: str = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
    
    # Timetable table
    timetable_catalog: str = os.getenv("TIMETABLE_CATALOG", "workspace")
    timetable_schema: str = os.getenv("TIMETABLE_SCHEMA", "default")
    timetable_table: str = os.getenv("TIMETABLE_TABLE", "mca_timetable")
    
    # LLM
    llm_endpoint: str = os.getenv("LLM_ENDPOINT", "databricks-gpt-oss-120b")
    llm_model: str = os.getenv("LLM_MODEL", "databricks-gpt-oss-120b")
    
    # App
    app_name: str = "MCA Timetable Intelligent Assistant"
    max_tool_calls: int = 3
    max_history: int = 10
    
    @property
    def timetable_table_full(self) -> str:
        return f"{self.timetable_catalog}.{self.timetable_schema}.{self.timetable_table}"
    
    @property
    def databricks_sql_url(self) -> str:
        host = self.databricks_host.rstrip("/")
        return f"{host}/sql/1.0/warehouses/{self.warehouse_id}"
    
    @property
    def llm_url(self) -> str:
        host = self.databricks_host.rstrip("/")
        return f"{host}/serving-endpoints/{self.llm_endpoint}/invocations"
    
    def validate(self) -> list[str]:
        """Return a list of missing required configuration values."""
        missing = []
        if not self.databricks_host:
            missing.append("DATABRICKS_HOST")
        if not self.warehouse_id:
            missing.append("DATABRICKS_WAREHOUSE_ID")
        return missing


# Singleton config instance
config = Config()

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
    "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
}

# Fixed break slots to always display in timetable output
FIXED_BREAKS = [
    {"start": "10:40", "end": "10:50", "label": "\u2615 Short Break"},
    {"start": "12:50", "end": "13:20", "label": "\U0001f37d Lunch Break"},
    {"start": "15:20", "end": "15:30", "label": "\u2615 Short Break"},
]
