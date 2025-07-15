from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal, Union
from datetime import date
import json
from execute_query import execute_query

app = FastAPI()

# Data models
class SalesRecord(BaseModel):
    id: str
    beneficiaryRegion: int
    gender: int
    age: int
    genericNumber: int
    totalBoxes: int
    regions: Dict[str, int]
    company: str
    drugName: str
    drugType: Literal['brand', 'generic']
    revenue: float
    date: str
    growth: Optional[float] = None
    prescriber: Optional[str] = None
    volumeShare: Optional[float] = None
    region: Optional[str] = None

class KPIData(BaseModel):
    totalRevenue: float
    revenueChange: float
    totalUnits: int
    unitsChange: float
    genericRatio: float
    genericRatioChange: float
    activeCompanies: int
    companiesChange: float

# New models for execute_query response
class UnifiedRecord(BaseModel):
    total_boites: float
    Region: str
    Sex: str
    Age: str
    Medication: Optional[str] = None
    Generic: Optional[str] = None
    
    # Prescriber fields
    General_Medical_Practice_Private: float = 0.0
    Anesthesiology_Intensive_Care_Private: float = 0.0
    Cardiovascular_Pathology_Private: float = 0.0
    Surgical_Medicine_Private: float = 0.0
    Dermatology_Venereology_Private: float = 0.0
    Radiology_Private: float = 0.0
    Obstetrics_Gynecology_Private: float = 0.0
    Gastroenterology_Hepatology_Private: float = 0.0
    Internal_Medicine_Private: float = 0.0
    Otorhinolaryngology_ENT_Private: float = 0.0
    Pediatrics_Private: float = 0.0
    Pulmonology_Private: float = 0.0
    Rheumatology_Private: float = 0.0
    Ophthalmology_Private: float = 0.0
    Psychiatry_Private: float = 0.0
    Dental_Surgery: float = 0.0
    Physical_Medicine_Rehabilitation_Private: float = 0.0
    Neurology_Private: float = 0.0
    Nephrology_Private: float = 0.0
    Dental_Surgery_Orthodontic_Specialist: float = 0.0
    Anatomical_Cytopathology_Private: float = 0.0
    Director_of_Medical_Laboratory_Private: float = 0.0
    Endocrinology_Metabolism_Private: float = 0.0
    Salaried_Prescribers: float = 0.0
    Non_Physician_City_Prescribers: float = 0.0
    Unknown_Specialty: float = 0.0

    class Config:
        alias_generator = lambda x: x.replace('_', ' ').replace('Private', '(Private)')

class MetricsRecord(BaseModel):
    brand_total: float
    generic_total: float
    combined_total: float
    brand_share: float
    Region: Optional[str] = None
    Sex: Optional[str] = None
    Age: Optional[str] = None
    Prescriber: Optional[str] = None

class ExecuteQueryResponse(BaseModel):
    unified_df: List[UnifiedRecord]
    unified_df_gen: List[UnifiedRecord]
    metrics: Dict[str, List[MetricsRecord]]

# Parameter models
class SalesDataParams(BaseModel):
    cip13_codes: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    drug_type: Optional[Literal['brand', 'generic', 'all']] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    age_groups: Optional[List[int]] = None
    gender: Optional[List[int]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

class TimeSeriesParams(SalesDataParams):
    granularity: Literal['daily', 'weekly', 'monthly', 'quarterly']
    metrics: List[Literal['revenue', 'units', 'market_share']]

class RegionalParams(SalesDataParams):
    aggregation_level: Literal['region', 'department']
    metric: Literal['revenue', 'units', 'market_share']

# Mock data
mock_sales = [
    SalesRecord(
        id="1",
        beneficiaryRegion=5,
        gender=1,
        age=20,
        genericNumber=813,
        totalBoxes=3718,
        regions={"1": 3072, "2": 0, "3": 33, "35": 35, "42": 467, "99": 111},
        company="Sanofi",
        drugName="Doliprane",
        drugType="brand",
        revenue=185900,
        date="2024-01-15"
    ),
    SalesRecord(
        id="2",
        beneficiaryRegion=5,
        gender=1,
        age=20,
        genericNumber=814,
        totalBoxes=9625,
        regions={"1": 8009, "2": 0, "3": 148, "35": 68, "42": 1087, "99": 313},
        company="Pfizer",
        drugName="Generic Paracetamol",
        drugType="generic",
        revenue=481250,
        date="2024-01-16"
    ),
]

mock_kpis = KPIData(
    totalRevenue=45600000,
    revenueChange=12.5,
    totalUnits=2340000,
    unitsChange=8.7,
    genericRatio=34.2,
    genericRatioChange=-2.1,
    activeCompanies=45,
    companiesChange=5.0
)

# Endpoints
@app.get("/api/v1/sales", response_model=List[SalesRecord])
def get_sales(
    cip13_codes: Optional[List[str]] = Query(None),
    companies: Optional[List[str]] = Query(None),
    regions: Optional[List[str]] = Query(None),
    drug_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    age_groups: Optional[List[int]] = Query(None),
    gender: Optional[List[int]] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None)
):
    # Filtering logic can be added here
    return mock_sales

@app.get("/api/v1/kpis", response_model=KPIData)
def get_kpis():
    return mock_kpis

# @app.get("/api/v1/sales/timeseries")
# def get_timeseries():
#     return {"message": "Mock time series data"}

# @app.get("/api/v1/sales/regional")
# def get_regional():
#     return {"message": "Mock regional data"}

@app.get("/api/v1/sales/companies")
def get_company_comparison():
    return {"message": "Mock company comparison data"}

# @app.get("/api/v1/sales/drugs")
# def get_drug_analysis():
#     return {"message": "Mock drug analysis data"}

# @app.get("/api/v1/sales/market-share")
# def get_market_share():
#     return {"message": "Mock market share data"}

# @app.get("/api/v1/analytics/forecast")
# def get_forecast():
#     return {"message": "Mock forecast data"}

# @app.get("/api/v1/analytics/anomalies")
# def get_anomalies():
#     return {"message": "Mock anomalies data"}

# @app.get("/api/v1/master/companies")
# def get_companies():
#     return ["Sanofi", "Pfizer", "Novartis"]

# @app.get("/api/v1/master/drugs")
# def get_drugs():
#     return ["Doliprane", "Generic Paracetamol"]

@app.get("/api/v1/master/regions")
def get_regions():
    return ["1", "2", "3", "35", "42", "99"]

@app.get("/api/v1/execute-query", response_model=ExecuteQueryResponse)
def get_execute_query(cip_list: List[str] = Query(...), gen_list: List[str] = Query(...)):
    result = execute_query(cip_list, gen_list)
    return result

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 