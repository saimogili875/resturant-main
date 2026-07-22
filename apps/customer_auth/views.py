import time

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.customer_auth.forms import CustomerLoginForm, OTPVerifyForm
from apps.customer_auth.models import Customer
from apps.customer_auth import services


def get_logged_in_customer(request) -> Customer | None:
    """Helper function to fetch the currently logged-in Customer from session."""
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return None
    try:
        return Customer.objects.filter(pk=customer_id).first()
    except Exception:
        return None


@require_http_methods(["GET", "POST"])
def customer_login(request):
    """Customer login/signup page — accepts phone and email to trigger OTP delivery."""
    # If already logged in, redirect to checkout or menu
    if get_logged_in_customer(request):
        cart_raw = request.session.get("delv_cart", {})
        if cart_raw:
            return redirect("orders_customer:checkout")
        return redirect("orders_customer:menu")

    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            email = form.cleaned_data["email"]

            # Rate limit check
            is_allowed, remaining = services.check_rate_limit(phone, email)
            if not is_allowed:
                messages.error(
                    request,
                    "Too many OTP requests for this phone/email. Please wait 10 minutes before requesting a new code.",
                )
                return render(request, "customer_auth/login.html", {"form": form})

            # Generate OTP & store hashed in Redis
            otp = services.generate_otp()
            services.store_otp_in_redis(phone, email, otp)
            services.increment_rate_limit(phone, email)

            # Deliver OTP via Gmail SMTP
            sent = services.send_otp_email(email, otp)
            if not sent:
                messages.error(
                    request,
                    "Could not send verification email. Please verify your email address and try again.",
                )
                return render(request, "customer_auth/login.html", {"form": form})

            # Store transient session info for verification step
            request.session["pending_otp_phone"] = phone
            request.session["pending_otp_email"] = email
            request.session["pending_otp_timestamp"] = int(time.time())
            request.session.modified = True

            messages.success(request, f"We've sent a verification code to {email}")
            return redirect("customer_auth:verify_otp")
    else:
        # Pre-fill phone/email if user had partial session data
        initial = {}
        if "pending_otp_phone" in request.session:
            initial["phone"] = request.session["pending_otp_phone"]
        if "pending_otp_email" in request.session:
            initial["email"] = request.session["pending_otp_email"]
        form = CustomerLoginForm(initial=initial)

    return render(request, "customer_auth/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_otp(request):
    """OTP verification page — customer enters the 6-digit code received via email."""
    phone = request.session.get("pending_otp_phone")
    email = request.session.get("pending_otp_email")
    timestamp = request.session.get("pending_otp_timestamp", 0)

    if not phone or not email:
        messages.warning(request, "Please enter your phone number and email to receive a verification code.")
        return redirect("customer_auth:login")

    # Calculate remaining cooldown seconds from actual send timestamp
    elapsed = int(time.time()) - timestamp
    cooldown_left = max(0, 45 - elapsed)

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data["otp"]
            is_valid = services.verify_otp_in_redis(phone, email, otp)

            if is_valid:
                # Fetch or create Customer record
                customer, created = Customer.objects.get_or_create(
                    phone=phone,
                    email=email,
                    defaults={"name": ""},
                )
                if not created:
                    customer.save()  # Triggers auto_now update on last_login_at

                # Set 30-day long-lived session
                request.session["customer_id"] = customer.pk
                request.session.set_expiry(30 * 24 * 3600)  # 30 days

                # Clean transient pending session keys
                request.session.pop("pending_otp_phone", None)
                request.session.pop("pending_otp_email", None)
                request.session.pop("pending_otp_timestamp", None)
                request.session.modified = True

                messages.success(request, f"Successfully signed in as {customer.email}!")

                # Redirect to checkout if customer has items in delivery cart
                cart_raw = request.session.get("delv_cart", {})
                if cart_raw:
                    return redirect("orders_customer:checkout")
                return redirect("orders_customer:menu")
            else:
                messages.error(
                    request,
                    "Invalid or expired verification code. Please check your code or request a new one.",
                )
    else:
        form = OTPVerifyForm()

    context = {
        "form": form,
        "phone": phone,
        "email": email,
        "cooldown_left": cooldown_left,
    }
    return render(request, "customer_auth/verify_otp.html", context)


@require_POST
def resend_otp(request):
    """AJAX/POST endpoint to resend OTP with rate limiting."""
    phone = request.session.get("pending_otp_phone")
    email = request.session.get("pending_otp_email")

    if not phone or not email:
        messages.error(request, "Session expired. Please enter your email and phone number again.")
        return redirect("customer_auth:login")

    is_allowed, remaining = services.check_rate_limit(phone, email)
    if not is_allowed:
        messages.error(
            request,
            "Too many OTP requests. Please wait 10 minutes before requesting a new code.",
        )
        return redirect("customer_auth:verify_otp")

    otp = services.generate_otp()
    services.store_otp_in_redis(phone, email, otp)
    services.increment_rate_limit(phone, email)

    sent = services.send_otp_email(email, otp)
    if sent:
        request.session["pending_otp_timestamp"] = int(time.time())
        request.session.modified = True
        messages.success(request, f"We've sent a verification code to {email}")
    else:
        messages.error(request, "Failed to send email. Please try again.")

    return redirect("customer_auth:verify_otp")


@require_http_methods(["GET", "POST"])
def customer_logout(request):
    """Customer logout — clears customer session and returns to delivery menu."""
    if "customer_id" in request.session:
        del request.session["customer_id"]
        request.session.set_expiry(0)
        request.session.modified = True
        messages.success(request, "You have been logged out.")
    return redirect("orders_customer:menu")
