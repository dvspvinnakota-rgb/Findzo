import uuid
from datetime import date
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.models import (
    OTPRequest, OTPVerify, UserProfile, Job, JobCreate, JobApplication, LocationUpdate, MealService,
    PaymentOrderRequest, PaymentVerificationRequest
)
from app.database import (
    get_jobs_db, insert_job_db, save_profile_db, create_application_db,
    record_payment_db, SUPABASE_SCHEMA_SQL, supabase_client
)
from app.payments import create_payment_order, verify_payment_signature
from app.mock_db import USER_PROFILES, SAVED_JOBS, JOB_APPLICATIONS

app = FastAPI(
    title="Findzo API",
    description="Backend API for Findzo Local Job Search & Staffing Platform (Supabase & Payments Integrated)",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    """Serve main single-page html client."""
    return FileResponse("static/index.html")

# --- DATABASE & CONFIGURATION STATUS ENDPOINTS ---

@app.get("/api/database/status")
def get_database_status():
    """Health check for Supabase and Payment Gateway integration."""
    return {
        "supabase": {
            "configured": config.is_supabase_configured(),
            "url": config.SUPABASE_URL if config.is_supabase_configured() else "Not Configured (Demo Mode)",
            "connected": supabase_client is not None
        },
        "razorpay": {
            "configured": config.is_razorpay_configured(),
            "key_id": config.RAZORPAY_KEY_ID if config.is_razorpay_configured() else "Demo Mode Key"
        },
        "environment": config.ENVIRONMENT
    }

@app.get("/api/database/schema")
def get_database_schema():
    """Returns the SQL table schema for Supabase setup."""
    return {
        "instructions": "Copy and execute this SQL script in your Supabase SQL Editor to create public tables.",
        "sql": SUPABASE_SCHEMA_SQL
    }

# --- AUTHENTICATION & ONBOARDING ENDPOINTS ---

@app.post("/api/auth/send-otp")
def send_otp(payload: OTPRequest):
    """Simulate sending 6-digit OTP to user mobile number."""
    mobile = payload.mobile.strip()
    if not mobile or len(mobile) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid 10-digit mobile number.")
    
    return {
        "status": "success",
        "message": f"OTP successfully sent to +91 {mobile[-10:]}",
        "demo_otp": "123456"
    }

@app.post("/api/auth/verify-otp")
def verify_otp(payload: OTPVerify):
    """Verify 6-digit OTP code and retrieve/create profile."""
    mobile = payload.mobile.strip()
    otp = payload.otp.strip()

    if otp != "123456" and len(otp) != 6:
        raise HTTPException(status_code=400, detail="Invalid OTP code. For demo, use 123456.")
    
    profile_data = {
        "mobile": mobile,
        "role": "seeker",
        "name": f"User_{mobile[-4:]}",
        "location": "Andheri West, Mumbai",
        "pincode": "400058",
        "skills": []
    }
    
    saved_profile = save_profile_db(profile_data)

    return {
        "status": "success",
        "message": "Mobile number verified successfully!",
        "token": f"findzo_session_{mobile[-4:]}_{uuid.uuid4().hex[:8]}",
        "profile": saved_profile
    }

@app.post("/api/auth/profile")
def update_profile(profile: UserProfile):
    """Save user onboarding role & location preferences."""
    saved = save_profile_db(profile.dict())
    return {
        "status": "success",
        "message": "Profile setup updated in database!",
        "profile": saved
    }

# --- JOB SEARCH & CATEGORY ENDPOINTS ---

@app.get("/api/categories")
def get_categories():
    """Return the supported catering and event services category."""
    all_jobs = get_jobs_db()
    return [
        {
            "id": "catering",
            "name": "Catering & Event Services",
            "count": sum(1 for job in all_jobs if job.get("category") == "catering"),
            "image": "/static/images/cat_catering.jpg",
            "description": "Waitstaff, event servers, and catering crews"
        }
    ]

@app.get("/api/jobs")
def get_jobs(
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    today: bool = Query(False),
    meal_service: Optional[MealService] = Query(None),
    fast_tag: Optional[str] = Query(None),
    rate_type: Optional[str] = Query(None),
    min_rate: Optional[float] = Query(None),
    max_rate: Optional[float] = Query(None),
    section: Optional[str] = Query(None)
):
    """Fetch and filter jobs from database."""
    all_jobs = get_jobs_db()
    filtered = [job for job in all_jobs if job.get("category") == "catering"]

    if section == "catering":
        filtered = [job for job in filtered if job.get("category") == "catering"]

    if category and category != "all":
        filtered = [j for j in filtered if j.get("category") == category.lower()]

    if keyword:
        kw = keyword.lower().strip()
        filtered = [
            j for j in filtered
            if kw in j.get("title", "").lower()
            or kw in j.get("description", "").lower()
            or kw in j.get("location", "").lower()
            or any(kw in str(tag).lower() for tag in j.get("tags", []))
        ]

    if pincode:
        pin = pincode.strip()
        if pin:
            filtered = [j for j in filtered if pin in j.get("pincode", "") or pin in j.get("location", "")]

    if location:
        location_query = location.lower().strip()
        filtered = [j for j in filtered if location_query in j.get("location", "").lower()]

    if today:
        today_date = date.today().isoformat()
        filtered = [j for j in filtered if j.get("event_date") == today_date]

    if meal_service:
        filtered = [j for j in filtered if meal_service in j.get("meal_services", [])]

    if fast_tag:
        tag_val = fast_tag.strip().lower()
        filtered = [
            j for j in filtered
            if any(tag_val in str(t).lower() for t in j.get("tags", []))
        ]

    if rate_type and rate_type != "all":
        filtered = [j for j in filtered if j.get("rate_type", "").lower() == rate_type.lower()]

    if min_rate is not None:
        filtered = [j for j in filtered if j.get("rate", 0) >= min_rate]

    if max_rate is not None:
        filtered = [j for j in filtered if j.get("rate", 0) <= max_rate]

    return {
        "count": len(filtered),
        "jobs": filtered
    }

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    """Retrieve details for a single job posting."""
    all_jobs = get_jobs_db()
    for job in all_jobs:
        if job["id"] == job_id:
            return job
    raise HTTPException(status_code=404, detail="Job not found")

@app.post("/api/jobs/{job_id}/apply")
def apply_job(job_id: str, payload: JobApplication):
    """Apply to a job or trigger direct call unlock."""
    all_jobs = get_jobs_db()
    target_job = None
    for job in all_jobs:
        if job["id"] == job_id:
            target_job = job
            break

    if not target_job:
        raise HTTPException(status_code=404, detail="Job not found")

    application_record = {
        "id": f"app_{uuid.uuid4().hex[:6]}",
        "job_id": job_id,
        "job_title": target_job["title"],
        "employer_name": target_job["employer_name"],
        "applicant_mobile": payload.applicant_mobile,
        "applicant_name": payload.applicant_name,
        "notes": payload.notes,
        "status": "Applied / Call Initiated",
        "contact_phone": target_job["contact_phone"]
    }
    
    saved_app = create_application_db(application_record)

    return {
        "status": "success",
        "message": f"Successfully applied for {target_job['title']}! Contact number unlocked: {target_job['contact_phone']}",
        "application": saved_app
    }

@app.post("/api/jobs/{job_id}/save")
def toggle_save_job(job_id: str, mobile: str = Query(...)):
    """Bookmark or unbookmark a job posting."""
    user_saved = SAVED_JOBS.get(mobile, [])
    if job_id in user_saved:
        user_saved.remove(job_id)
        is_saved = False
        msg = "Job removed from saved items"
    else:
        user_saved.append(job_id)
        is_saved = True
        msg = "Job saved to your bookmarks!"
    SAVED_JOBS[mobile] = user_saved

    return {
        "status": "success",
        "is_saved": is_saved,
        "message": msg,
        "saved_count": len(user_saved)
    }

@app.post("/api/jobs/create")
def create_new_job(payload: JobCreate):
    """Employer endpoint to post a new local job into database."""
    rate_str = f"₹{payload.rate:,.0f} / {payload.rate_type.lower()}"

    new_job = {
        "id": f"job-{payload.category[:4]}-{uuid.uuid4().hex[:4]}",
        "title": payload.title,
        "category": payload.category,
        "category_name": "Catering & Event Services",
        "rate": payload.rate,
        "rate_type": payload.rate_type,
        "rate_formatted": rate_str,
        "location": payload.location,
        "pincode": payload.pincode,
        "distance": "0.5 km away",
        "shift_timings": payload.shift_timings,
        "meal_services": payload.meal_services,
        "event_date": payload.event_date.isoformat() if payload.event_date else None,
        "employer_name": payload.employer_name,
        "employer_rating": 5.0,
        "verified_employer": True,
        "tags": payload.tags if payload.tags else ["New Opening", "Same-Day Start"],
        "description": payload.description,
        "urgent": payload.urgent,
        "tools_provided": payload.tools_provided,
        "transport_available": payload.transport_available,
        "contact_phone": payload.contact_phone,
        "applicants_count": 0
    }

    inserted_job = insert_job_db(new_job)

    return {
        "status": "success",
        "message": "Job successfully published and saved.",
        "job": inserted_job
    }

# --- PAYMENTS API ENDPOINTS ---

@app.post("/api/payments/create-order")
def api_create_payment_order(payload: PaymentOrderRequest):
    """Create a Razorpay payment order for job posting or employer verification."""
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount.")

    notes = {
        "purpose": payload.purpose,
        "user_mobile": payload.user_mobile or "9876543210",
        "job_id": payload.job_id or ""
    }
    
    order_data = create_payment_order(amount=payload.amount, currency="INR", notes=notes)
    return order_data

@app.post("/api/payments/verify")
def api_verify_payment(payload: PaymentVerificationRequest):
    """Verify Razorpay payment signature and record in database."""
    is_valid = verify_payment_signature(
        order_id=payload.order_id,
        payment_id=payload.payment_id,
        signature=payload.signature
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    payment_record = {
        "id": f"pay_{uuid.uuid4().hex[:8]}",
        "order_id": payload.order_id,
        "payment_id": payload.payment_id,
        "signature": payload.signature,
        "amount": 199.0,
        "currency": "INR",
        "status": "SUCCESS",
        "user_mobile": payload.user_mobile,
        "job_id": payload.job_id,
        "purpose": payload.purpose or "Employer Job Posting"
    }

    saved_payment = record_payment_db(payment_record)

    return {
        "status": "success",
        "message": "Payment verified successfully! Receipt generated.",
        "payment": saved_payment
    }
