import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.customer_auth.models import Customer
from apps.customer_auth import services


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_customer_model():
    cust = Customer.objects.create(
        phone="9876543210",
        email="customer@example.com",
        name="John Doe",
        default_address="123 Main St",
    )
    assert str(cust) == "Customer customer@example.com (9876543210)"
    assert cust.pk is not None


def test_otp_generation_and_hashing():
    otp1 = services.generate_otp()
    assert len(otp1) == 6
    assert otp1.isdigit()

    hash1 = services.hash_otp(otp1)
    hash2 = services.hash_otp(otp1)
    assert hash1 == hash2
    assert hash1 != otp1


def test_redis_otp_storage_and_verification():
    phone = "9876543210"
    email = "test@example.com"
    otp = "123456"

    # Store OTP
    services.store_otp_in_redis(phone, email, otp)

    # Wrong OTP fails
    assert not services.verify_otp_in_redis(phone, email, "654321")

    # Correct OTP succeeds
    assert services.verify_otp_in_redis(phone, email, otp)

    # Single-use: Second verification fails because OTP was deleted
    assert not services.verify_otp_in_redis(phone, email, otp)


def test_otp_rate_limiting():
    phone = "9876543210"
    email = "rate@example.com"

    for _ in range(3):
        is_allowed, _ = services.check_rate_limit(phone, email)
        assert is_allowed
        services.increment_rate_limit(phone, email)

    # 4th request exceeds rate limit
    is_allowed, remaining = services.check_rate_limit(phone, email)
    assert not is_allowed
    assert remaining == 0


@pytest.mark.django_db
def test_customer_login_and_otp_flow(client):
    # Step 1: GET login page
    login_url = reverse("customer_auth:login")
    res = client.get(login_url)
    assert res.status_code == 200

    # Step 2: POST login form
    post_data = {"phone": "9876543210", "email": "flow@example.com"}
    res = client.post(login_url, post_data)
    assert res.status_code == 302
    assert res.url == reverse("customer_auth:verify_otp")

    # Check email was sent
    assert len(mail.outbox) == 1
    assert "Your Cafe Rudra Verification Code" in mail.outbox[0].subject

    # Extract OTP code from mail body
    mail_body = mail.outbox[0].body
    import re
    match = re.search(r"(\d{6})", mail_body)
    assert match is not None
    otp_code = match.group(1)

    # Step 3: GET verify OTP page
    verify_url = reverse("customer_auth:verify_otp")
    res = client.get(verify_url)
    assert res.status_code == 200
    assert res.context["email"] == "flow@example.com"
    assert res.context["cooldown_left"] <= 45 and res.context["cooldown_left"] > 0

    # Step 3b: POST wrong OTP — page reloads with error message, but cooldown persists
    res_wrong = client.post(verify_url, {"otp": "000000"})
    assert res_wrong.status_code == 200
    assert "Invalid or expired verification code" in res_wrong.content.decode("utf-8")
    assert res_wrong.context["cooldown_left"] <= 45

    # Step 4: POST correct OTP
    res = client.post(verify_url, {"otp": otp_code})
    assert res.status_code == 302
    assert res.url == reverse("orders_customer:menu")

    # Verify Customer object created & session set
    customer = Customer.objects.get(email="flow@example.com")
    assert customer.phone == "9876543210"
    assert client.session.get("customer_id") == customer.pk

    # Step 5: Logout
    logout_url = reverse("customer_auth:logout")
    res = client.post(logout_url)
    assert res.status_code == 302
    assert client.session.get("customer_id") is None


@pytest.mark.django_db
def test_checkout_prefill_and_address_update(client):
    from decimal import Decimal
    from apps.menu.models import Category, MenuItem

    # Create category & menu item
    cat = Category.objects.create(name="Drinks", is_active=True)
    item = MenuItem.objects.create(category=cat, name="Coffee", price=Decimal("100"), is_available=True)

    # Create Customer
    customer = Customer.objects.create(
        phone="9876543210",
        email="prefill@example.com",
        name="Pre-filled Name",
        default_address="123 Saved Street",
    )

    # Add item to session cart & set logged in customer session
    session = client.session
    session["delv_cart"] = {str(item.pk): 2}
    session["customer_id"] = customer.pk
    session.save()

    # GET checkout page — verify form pre-filling
    checkout_url = reverse("orders_customer:checkout")
    res = client.get(checkout_url)
    assert res.status_code == 200
    assert res.context["form_data"]["contact_name"] == "Pre-filled Name"
    assert res.context["form_data"]["contact_phone"] == "9876543210"
    assert res.context["form_data"]["address"] == "123 Saved Street"

    # POST checkout with updated address
    post_data = {
        "contact_name": "Pre-filled Name",
        "contact_phone": "9876543210",
        "address": "456 New Delivery Address",
        "instructions": "Leave at front door",
    }
    res = client.post(checkout_url, post_data)
    assert res.status_code == 200

    # Refresh Customer and check updated default_address
    customer.refresh_from_db()
    assert customer.default_address == "456 New Delivery Address"


@pytest.mark.django_db
def test_guest_checkout_fallback(client):
    from decimal import Decimal
    from apps.menu.models import Category, MenuItem

    cat = Category.objects.create(name="Food", is_active=True)
    item = MenuItem.objects.create(category=cat, name="Burger", price=Decimal("250"), is_available=True)

    # Add item to cart without logging in
    session = client.session
    session["delv_cart"] = {str(item.pk): 1}
    session.save()

    checkout_url = reverse("orders_customer:checkout")
    res = client.get(checkout_url)
    assert res.status_code == 200
    assert res.context.get("delivery_customer") is None

    post_data = {
        "contact_name": "Guest Customer",
        "contact_phone": "9998887770",
        "address": "789 Guest Way",
        "instructions": "",
    }
    res = client.post(checkout_url, post_data)
    assert res.status_code == 200
    assert "thank_you" in res.templates[0].name

