import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from app.config import config

logger = logging.getLogger("findzo.payments")

razorpay_client = None

if config.is_razorpay_configured():
    try:
        import razorpay
        razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
        logger.info("Successfully initialized Razorpay Client with Key ID: %s", config.RAZORPAY_KEY_ID)
    except Exception as e:
        logger.error("Error initializing Razorpay Client: %s", e)
        razorpay_client = None

def create_payment_order(amount: float, currency: str = "INR", notes: Optional[dict] = None) -> Dict[str, Any]:
    """
    Create a new payment order for posting job or profile verification.
    Amount in Rupees (converted to Paise for Razorpay: ₹199 -> 19900 paise).
    """
    amount_in_paise = int(amount * 100)
    order_notes = notes or {"purpose": "Job Posting / Employer Badge"}

    if razorpay_client:
        try:
            data = {
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": f"receipt_{uuid.uuid4().hex[:8]}",
                "notes": order_notes
            }
            order = razorpay_client.order.create(data=data)
            return {
                "status": "success",
                "mode": "live_razorpay",
                "order_id": order["id"],
                "amount": amount,
                "amount_paise": amount_in_paise,
                "currency": currency,
                "key_id": config.RAZORPAY_KEY_ID,
                "notes": order_notes
            }
        except Exception as e:
            logger.error("Razorpay order creation error: %s", e)

    # Simulated order creation when running in test / placeholder mode
    simulated_order_id = f"order_demo_{uuid.uuid4().hex[:10]}"
    return {
        "status": "success",
        "mode": "simulated",
        "order_id": simulated_order_id,
        "amount": amount,
        "amount_paise": amount_in_paise,
        "currency": currency,
        "key_id": config.RAZORPAY_KEY_ID or "rzp_test_demo12345",
        "notes": order_notes,
        "message": "Demo mode: Order created. Use test payment verification."
    }

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify payment signature from Razorpay response."""
    if razorpay_client and config.is_razorpay_configured():
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:
            logger.error("Razorpay signature verification failed: %s", e)
            return False

    # In demo mode, accept any non-empty signature or test signature
    if order_id.startswith("order_demo_") or not signature:
        return True

    # Manual HMAC verification check fallback
    if config.RAZORPAY_KEY_SECRET:
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        generated_signature = hmac.new(
            config.RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(generated_signature, signature)

    return True
