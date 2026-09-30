import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Load environment variables from the project root .env file
load_dotenv(ENV_FILE, override=False)

class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def is_supabase_configured(cls) -> bool:
        """Check if real Supabase keys are configured."""
        return (
            bool(cls.SUPABASE_URL) and
            "xyzyourproject" not in cls.SUPABASE_URL and
            "your-project-id" not in cls.SUPABASE_URL and
            bool(cls.SUPABASE_ANON_KEY) and
            "your_anon_key" not in cls.SUPABASE_ANON_KEY
        )

    @classmethod
    def is_razorpay_configured(cls) -> bool:
        """Check if real Razorpay keys are configured."""
        return (
            bool(cls.RAZORPAY_KEY_ID) and
            "YourKeyIdHere" not in cls.RAZORPAY_KEY_ID and
            "your_key_id" not in cls.RAZORPAY_KEY_ID and
            bool(cls.RAZORPAY_KEY_SECRET)
        )

config = Config()
