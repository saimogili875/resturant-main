import hashlib
import random
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

OTP_TTL = 300  # 5 minutes
RATE_LIMIT_WINDOW = 600  # 10 minutes
MAX_OTP_REQUESTS = 3  # Max 3 requests per 10 minutes


def generate_otp() -> str:
    """Generate a random 6-digit numeric OTP code string."""
    return f"{random.randint(100000, 999999)}"


def hash_otp(otp: str) -> str:
    """Hash an OTP code using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _get_cache_keys(phone: str, email: str) -> tuple[str, str]:
    """Generate cache keys for OTP and rate limiting based on phone + email."""
    identifier = f"{phone.strip()}_{email.strip().lower()}"
    hashed_id = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:32]
    return f"cust_otp:{hashed_id}", f"cust_otp_rate:{hashed_id}"


def check_rate_limit(phone: str, email: str) -> tuple[bool, int]:
    """Check if the user has exceeded the rate limit (max 3 requests per 10 mins).

    Returns (is_allowed, remaining_attempts).
    """
    _, rate_key = _get_cache_keys(phone, email)
    current_count = cache.get(rate_key, 0)
    if current_count >= MAX_OTP_REQUESTS:
        return False, 0
    return True, MAX_OTP_REQUESTS - current_count


def increment_rate_limit(phone: str, email: str) -> None:
    """Increment rate limit counter in Redis/cache."""
    _, rate_key = _get_cache_keys(phone, email)
    try:
        if cache.get(rate_key) is None:
            cache.set(rate_key, 1, timeout=RATE_LIMIT_WINDOW)
        else:
            cache.incr(rate_key)
    except Exception:
        # Fallback if cache incr fails on new key
        cache.set(rate_key, 1, timeout=RATE_LIMIT_WINDOW)


def store_otp_in_redis(phone: str, email: str, otp: str) -> None:
    """Store the SHA-256 hashed OTP in Redis with a 5-minute expiry."""
    otp_key, _ = _get_cache_keys(phone, email)
    hashed_code = hash_otp(otp)
    cache.set(otp_key, hashed_code, timeout=OTP_TTL)


def verify_otp_in_redis(phone: str, email: str, input_otp: str) -> bool:
    """Verify input OTP against hashed OTP in Redis.

    Deletes the OTP key upon successful verification (single-use).
    """
    otp_key, _ = _get_cache_keys(phone, email)
    stored_hash = cache.get(otp_key)
    if not stored_hash:
        return False

    input_hash = hash_otp(input_otp)
    if input_hash == stored_hash:
        cache.delete(otp_key)  # Single-use: delete after verification
        return True
    return False


import logging

logger = logging.getLogger(__name__)


def send_otp_email(email: str, otp: str) -> bool:
    """Send OTP code to customer's email via Gmail SMTP.

    Never logs the plaintext OTP.
    """
    subject = "Your Cafe Rudra Verification Code"
    message = (
        f"Hello,\n\n"
        f"Your verification code for Cafe Rudra Delivery is: {otp}\n\n"
        f"This code will expire in 5 minutes. Please do not share this code with anyone.\n\n"
        f"Thank you,\n"
        f"RDH · Cafe Rudra"
    )
    email_user = getattr(settings, "EMAIL_HOST_USER", "")
    email_pass = getattr(settings, "EMAIL_HOST_PASSWORD", "")
    if not email_user or not email_pass:
        logger.error(
            f"CANNOT SEND OTP EMAIL: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD environment variable is blank in settings! "
            f"(EMAIL_HOST_USER='{email_user}', EMAIL_HOST_PASSWORD={'[SET]' if email_pass else '[BLANK]'})"
        )
        return False

    logger.info(
        f"Sending OTP email to {email} using host={settings.EMAIL_HOST}:{settings.EMAIL_PORT}, user={email_user}"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or email_user

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Successfully sent OTP email to {email}")
        return True
    except Exception as exc:
        logger.exception(f"Failed to send OTP email to {email} (host={settings.EMAIL_HOST}, user={settings.EMAIL_HOST_USER}): {exc}")
        return False
