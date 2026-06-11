from pydantic import BaseModel
from typing import List, Optional

class ForecastResponse(BaseModel):
    store_id: str
    item_id: str
    horizon: int
    dates: List[str]
    forecast: List[float]
    total_forecast_units: float

class RecommendResponse(BaseModel):
    user_id: int
    variant: str
    items: List[dict]

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]

class KPIResponse(BaseModel):
    kpi_date: str
    total_orders: int
    unique_customers: int
    total_units: int
    total_revenue: float
    avg_basket_size: float
    revenue_wow_pct: Optional[float]
    is_revenue_spike: bool

class AlertResponse(BaseModel):
    alert_id: str
    created_at: str
    severity: str
    title: str
    message: str
    recommended_action: str

class AgentReportResponse(BaseModel):
    report_id: str
    created_at: str
    report: str

class ABTestResults(BaseModel):
    variant: str
    impressions: int
    avg_items_shown: float
