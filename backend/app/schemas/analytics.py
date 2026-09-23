from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import date

class DailyTrend(BaseModel):
    date: str
    count: int

class TripAnalytics(BaseModel):
    total: int
    completed: int
    cancelled: int
    active: int
    scheduled: int
    trend: List[DailyTrend]

class AlertAnalytics(BaseModel):
    total: int
    active: int
    resolved: int
    by_type: Dict[str, int]
    trend: List[DailyTrend]

class EmergencyAnalytics(BaseModel):
    total: int
    active: int
    acknowledged: int
    resolved: int
    by_type: Dict[str, int]
    trend: List[DailyTrend]

class BusUtilization(BaseModel):
    bus_id: int
    bus_number: str
    trips: int
    completed: int
    cancelled: int
    active: int

class DriverOperations(BaseModel):
    driver_id: int
    driver_name: str
    trips: int
    completed: int
    cancelled: int
    emergencies: int

class RoutePerformance(BaseModel):
    route_id: int
    route_name: str
    trips: int
    completed: int
    cancelled: int
    alerts: int
    emergencies: int

class AnalyticsSummaryResponse(BaseModel):
    trips: TripAnalytics
    alerts: AlertAnalytics
    emergencies: EmergencyAnalytics
    buses: List[BusUtilization]
    drivers: List[DriverOperations]
    routes: List[RoutePerformance]
