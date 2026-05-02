from pydantic import BaseModel, validator, Field
from typing import Optional

class CustomerData(BaseModel):
    """Complete validation model for customer churn prediction input"""
    
    gender: str = Field(..., pattern="^(Male|Female)$", description="Customer gender", example="Female")
    SeniorCitizen: int = Field(..., ge=0, le=1, description="Senior citizen flag", example=0)
    Partner: str = Field(..., pattern="^(Yes|No)$", description="Has partner", example="Yes")
    Dependents: str = Field(..., pattern="^(Yes|No)$", description="Has dependents", example="No")
    tenure: int = Field(..., ge=0, le=72, description="Months with company", example=12)
    PhoneService: str = Field(..., pattern="^(Yes|No)$", description="Has phone service", example="Yes")
    MultipleLines: str = Field(..., pattern="^(Yes|No|No phone service)$", description="Multiple lines", example="No")
    InternetService: str = Field(..., pattern="^(DSL|Fiber optic|No)$", description="Internet service type", example="DSL")
    OnlineSecurity: str = Field(..., pattern="^(Yes|No|No internet service)$", description="Online security", example="No")
    OnlineBackup: str = Field(..., pattern="^(Yes|No|No internet service)$", description="Online backup", example="Yes")
    DeviceProtection: str = Field(..., pattern="^(Yes|No|No internet service)$", description="Device protection", example="No")
    TechSupport: str = Field(..., pattern="^(Yes|No|No internet service)$", description="Tech support", example="No")
    StreamingTV: str = Field(..., pattern="^(Yes|No|No internet service)$", description="TV streaming", example="Yes")
    StreamingMovies: str = Field(..., pattern="^(Yes|No|No internet service)$", description="Movie streaming", example="No")
    Contract: str = Field(..., pattern="^(Month-to-month|One year|Two year)$", description="Contract type", example="Month-to-month")
    PaperlessBilling: str = Field(..., pattern="^(Yes|No)$", description="Paperless billing", example="Yes")
    PaymentMethod: str = Field(
        ..., 
        pattern="^(Electronic check|Mailed check|Bank transfer \\(automatic\\)|Credit card \\(automatic\\))$",
        description="Payment method", 
        example="Electronic check"
    )
    MonthlyCharges: float = Field(..., gt=0, le=200, description="Monthly charges", example=29.85)
    TotalCharges: float = Field(..., gt=0, le=10000, description="Total charges", example=350.20)
    
    @validator('TotalCharges')
    def validate_total_charges(cls, v, values):
        if 'MonthlyCharges' in values and values['MonthlyCharges'] > 0:
            min_expected = values['MonthlyCharges']
            max_expected = values['MonthlyCharges'] * 72
            if v < min_expected or v > max_expected:
                raise ValueError(f'TotalCharges should be between {min_expected} and {max_expected} for tenure up to 72 months')
        return v
    
    @validator('tenure')
    def validate_tenure_with_contract(cls, v, values):
        if 'Contract' in values:
            if values['Contract'] == 'Month-to-month' and v > 24:
                raise ValueError('Month-to-month contract with tenure > 24 months is unusual')
            if values['Contract'] == 'One year' and v < 12:
                raise ValueError('One year contract with tenure < 12 months')
            if values['Contract'] == 'Two year' and v < 24:
                raise ValueError('Two year contract with tenure < 24 months')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 12,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "DSL",
                "OnlineSecurity": "No",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "Yes",
                "StreamingMovies": "No",
                "Contract": "Month-to-month",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 29.85,
                "TotalCharges": 350.20
            }
        }