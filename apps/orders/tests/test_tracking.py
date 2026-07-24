"""Anti-IDOR tests for the guest delivery tracking page.

Only the guest holding the signed ``delv_token_<pk>`` cookie set at checkout
(or the assigned agent / an admin) may load the tracking page; everyone else
gets a 404.
"""
from decimal import Decimal

import pytest
from django.core.signing import get_cookie_signer

from apps.orders.models import Order, OrderStatus

_TRACKING_SALT = "delv_tracking"


@pytest.fixture
def order(db):
    return Order.objects.create(
        order_type="DELV",
        status=OrderStatus.READY,
        total_amount=Decimal("30.00"),
        contact_name="Sam",
        contact_phone="555-0199",
    )


def _sign_token(order):
    """Reproduce the signed cookie value set by delivery_checkout()."""
    key = f"delv_token_{order.pk}"
    return get_cookie_signer(salt=key + _TRACKING_SALT).sign(str(order.pk))


@pytest.fixture
def customer_client(client, db):
    from apps.customer_auth.models import Customer
    cust = Customer.objects.create(phone="9876543210", email="track@example.com")
    session = client.session
    session["customer_id"] = cust.pk
    session.save()
    return client


@pytest.mark.django_db
def test_owner_cookie_can_track(customer_client, order):
    """The signed tracking cookie grants access and shows the live status text."""
    customer_client.cookies[f"delv_token_{order.pk}"] = _sign_token(order)

    response = customer_client.get(f"/order/{order.pk}/track/")

    assert response.status_code == 200
    # Live status text reflects the order's current status.
    assert order.get_status_display() in response.content.decode()


@pytest.mark.django_db
def test_non_owner_without_cookie_gets_404(customer_client, order):
    """A visitor with no tracking cookie cannot reach the order (anti-IDOR)."""
    response = customer_client.get(f"/order/{order.pk}/track/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_tampered_cookie_gets_404(customer_client, order):
    """A cookie with a bad signature is rejected, not trusted."""
    customer_client.cookies[f"delv_token_{order.pk}"] = "not-a-valid-signed-value"
    response = customer_client.get(f"/order/{order.pk}/track/")
    assert response.status_code == 404
