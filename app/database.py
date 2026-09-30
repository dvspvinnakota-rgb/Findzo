from typing import List, Dict, Optional
import json
import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from app.config import config
from app.mock_db import MOCK_JOBS, USER_PROFILES, SAVED_JOBS, JOB_APPLICATIONS

logger = logging.getLogger("findzo.database")
LOCAL_JOBS_DB_PATH = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "Findzo" / "jobs.sqlite3"


def _get_local_jobs() -> List[dict]:
    LOCAL_JOBS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(LOCAL_JOBS_DB_PATH)) as connection:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            rows = connection.execute("SELECT data FROM jobs ORDER BY rowid DESC").fetchall()
    return [json.loads(row[0]) for row in rows]


def _save_local_job(job_data: dict) -> dict:
    LOCAL_JOBS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(LOCAL_JOBS_DB_PATH)) as connection:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO jobs (id, data) VALUES (?, ?)",
                (job_data["id"], json.dumps(job_data)),
            )
    return job_data

# Initialize Supabase client if configured
supabase_client = None

if config.is_supabase_configured():
    try:
        from supabase import create_client, Client
        supabase_client: Optional[Client] = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
        logger.info("Successfully initialized Supabase Client connected to: %s", config.SUPABASE_URL)
    except Exception as e:
        logger.error("Error initializing Supabase Client: %s", e)
        supabase_client = None

# SQL Schema for Supabase Table Creation (Copy & paste into Supabase SQL Editor)
SUPABASE_SCHEMA_SQL = """
-- 1. Create Jobs Table
CREATE TABLE IF NOT EXISTS public.jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category = 'catering'),
    category_name TEXT NOT NULL,
    rate NUMERIC NOT NULL,
    rate_type TEXT NOT NULL,
    rate_formatted TEXT NOT NULL,
    location TEXT NOT NULL,
    pincode TEXT NOT NULL,
    distance TEXT DEFAULT '0.5 km away',
    shift_timings TEXT NOT NULL,
    employer_name TEXT NOT NULL,
    employer_rating NUMERIC DEFAULT 5.0,
    verified_employer BOOLEAN DEFAULT true,
    tags TEXT[] DEFAULT '{}',
    description TEXT,
    urgent BOOLEAN DEFAULT false,
    uniform_required TEXT,
    tools_provided BOOLEAN DEFAULT false,
    transport_available BOOLEAN DEFAULT false,
    event_date TEXT,
    meal_services TEXT[] NOT NULL DEFAULT '{}',
    contact_phone TEXT NOT NULL,
    applicants_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'jobs_category_catering_only'
          AND conrelid = 'public.jobs'::regclass
    ) THEN
        ALTER TABLE public.jobs
        ADD CONSTRAINT jobs_category_catering_only
        CHECK (category = 'catering') NOT VALID;
    END IF;
END $$;

ALTER TABLE public.jobs
ADD COLUMN IF NOT EXISTS meal_services TEXT[] NOT NULL DEFAULT '{}';

-- 2. Create User Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    mobile TEXT PRIMARY KEY,
    role TEXT DEFAULT 'seeker',
    name TEXT,
    location TEXT,
    pincode TEXT,
    skills TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Create Applications Table
CREATE TABLE IF NOT EXISTS public.applications (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES public.jobs(id),
    applicant_mobile TEXT NOT NULL,
    applicant_name TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'Applied / Call Initiated',
    contact_phone TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. Create Payments Table
CREATE TABLE IF NOT EXISTS public.payments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    payment_id TEXT,
    signature TEXT,
    amount NUMERIC NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL,
    user_mobile TEXT,
    job_id TEXT,
    purpose TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Enable RLS & Allow Anonymous Read/Write for Demo
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Read Jobs" ON public.jobs FOR SELECT USING (true);
CREATE POLICY "Public Insert Jobs" ON public.jobs FOR INSERT WITH CHECK (true);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Profiles" ON public.profiles FOR ALL USING (true);

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Applications" ON public.applications FOR ALL USING (true);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Payments" ON public.payments FOR ALL USING (true);
"""

# Database Interface Helper Functions
HIDDEN_DEMO_JOB_IDS = {"job-cat-01", "job-cat-04"}

def get_jobs_db() -> List[dict]:
    """Fetch all jobs from Supabase or fallback store."""
    local_jobs = _get_local_jobs()
    if supabase_client:
        try:
            res = supabase_client.table("jobs").select("*").order("created_at", desc=True).execute()
            if res.data is not None:
                remote_jobs = [
                    job for job in res.data
                    if job.get("category") == "catering" and job.get("id") not in HIDDEN_DEMO_JOB_IDS
                ]
                remote_ids = {job.get("id") for job in remote_jobs}
                return [job for job in local_jobs if job.get("id") not in remote_ids] + remote_jobs
        except Exception as e:
            logger.warning("Supabase fetch failed, using fallback mock data: %s", e)
    return local_jobs + MOCK_JOBS

def insert_job_db(job_data: dict) -> dict:
    """Insert a new job posting into Supabase or fallback store."""
    if job_data.get("category") != "catering":
        raise ValueError("Only Catering & Event Services jobs are supported.")

    if supabase_client:
        try:
            res = supabase_client.table("jobs").insert(job_data).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error("Error inserting job to Supabase: %s", e)

    return _save_local_job(job_data)

def save_profile_db(profile_data: dict) -> dict:
    """Upsert user profile in Supabase or fallback store."""
    if supabase_client:
        try:
            res = supabase_client.table("profiles").upsert(profile_data).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error("Error saving profile to Supabase: %s", e)

    USER_PROFILES[profile_data["mobile"]] = profile_data
    return profile_data

def create_application_db(app_data: dict) -> dict:
    """Record job application in Supabase or fallback store."""
    if supabase_client:
        try:
            res = supabase_client.table("applications").insert(app_data).execute()
            # Also increment applicants count on jobs table
            supabase_client.rpc("increment_applicants", {"job_id_param": app_data["job_id"]}).execute()
        except Exception as e:
            logger.error("Error inserting application to Supabase: %s", e)

    JOB_APPLICATIONS.append(app_data)
    return app_data

def record_payment_db(payment_data: dict) -> dict:
    """Record payment transaction in Supabase or fallback store."""
    if supabase_client:
        try:
            res = supabase_client.table("payments").insert(payment_data).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error("Error inserting payment to Supabase: %s", e)
    return payment_data
