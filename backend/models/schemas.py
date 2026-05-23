from pydantic import BaseModel, Field

# -----------------------------------------------------------------
# Pydantic Models (Data Contracts for Serialization/Deserialization)
# -----------------------------------------------------------------

class EntityOnboardingCreate(BaseModel):
    """
    This defines the exact JSON structure React MUST send when onboarding a new entity.
    """
    company_name: str = Field(..., description="Name of the corporate entity")
    cin: str = Field(..., description="Corporate Identification Number")
    pan: str = Field(..., description="Permanent Account Number")
    sector: str = Field(..., description="Industry sector (e.g., Manufacturing, IT)")
    loan_type: str = Field(..., description="Type of loan requested")
    loan_amount: float = Field(..., description="Total loan amount requested")
    loan_tenure_months: int = Field(..., description="Duration of the loan in months")

class EntityResponse(EntityOnboardingCreate):
    """
    This defines what FastAPI will send BACK to React. 
    It inherits everything from above, but adds a database ID.
    """
    id: int

    class Config:
        from_attributes = True # Tells Pydantic to read standard Python ORM objects