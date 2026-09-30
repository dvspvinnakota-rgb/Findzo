from datetime import date
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

MealService = Literal["lunch", "dinner", "breakfast+lunch+dinner", "lunch+dinner"]

class OTPRequest(BaseModel):
    mobile: str = Field(..., example="9876543210")

class OTPVerify(BaseModel):
    mobile: str
    otp: str

class UserProfile(BaseModel):
    mobile: str
    role: str = "seeker"  # 'seeker' or 'employer'
    name: Optional[str] = "Worker / Job Seeker"
    location: Optional[str] = "Andheri East, Mumbai"
    pincode: Optional[str] = "400069"
    skills: List[str] = []

class Job(BaseModel):
    id: str
    title: str
    category: str
    category_name: str
    rate: float
    rate_type: str  # 'Daily', 'Hourly', 'Per Event'
    rate_formatted: str
    location: str
    pincode: str
    distance: str
    shift_timings: str
    employer_name: str
    employer_rating: float
    verified_employer: bool = True
    tags: List[str]
    description: str
    urgent: bool = False
    uniform_required: Optional[str] = None
    tools_provided: Optional[bool] = None
    transport_available: Optional[bool] = None
    event_date: Optional[str] = None
    meal_services: List[str] = Field(default_factory=list)
    contact_phone: str
    applicants_count: int = 0

class JobCreate(BaseModel):
    title: str
    category: Literal["catering"]
    rate: float
    rate_type: str
    location: str
    pincode: str
    shift_timings: str
    employer_name: str
    contact_phone: str
    description: str
    tags: List[str] = []
    urgent: bool = False
    tools_provided: bool = False
    transport_available: bool = False
    meal_services: List[MealService] = Field(default_factory=list)
    event_date: Optional[date] = None

class JobApplication(BaseModel):
    job_id: str
    applicant_mobile: str
    applicant_name: str
    notes: Optional[str] = ""

class LocationUpdate(BaseModel):
    location: str
    pincode: str

# Payment Gateway Schemas
class PaymentOrderRequest(BaseModel):
    amount: float = Field(..., example=199.0)  # Amount in INR
    purpose: str = Field(..., example="Employer Premium Job Posting")
    user_mobile: Optional[str] = "9876543210"
    job_id: Optional[str] = None

class PaymentVerificationRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str
    user_mobile: Optional[str] = "9876543210"
    job_id: Optional[str] = None
    purpose: Optional[str] = "Job Posting"
