"""Tests for the admin transition endpoint.

Verifies that the thin POST endpoint delegates to services.transition correctly:
valid transitions succeed and write an OrderEvent, invalid ones are rejected,
and non-admin users get 403.
"""
from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.menu.models import Category, MenuItem
from apps.orders.models import OrderEvent, OrderStatus
from apps.orders.services import create_order


@pytest.fixture
def burger(db):
    category = Category.objects.create(name="Mains", is_active=True)
    return MenuItem.objects.create(
        category=category, name="Burger", price=Decimal("50.00"), is_available=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username="admin_t", password="pw", role=Role.ADMIN)


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(username="agent_t", password="pw", role=Role.AGENT)


@pytest.fixture
def placed_order(burger):
    """A freshly placed delivery order (status=PLACED)."""
    return create_order(
        order_type="DELV",
        items=[{"menu_item_id": burger.pk, "quantity": 2}],
    )


def _transition_url(pk):
    return f"/backoffice/orders/{pk}/transition/"


@pytest.mark.django_db
def test_valid_transition_succeeds(client, admin_user, placed_order):
    """PLACED -> APPROVED is allowed for ADMIN; writes an OrderEvent."""
    client.force_login(admin_user)
    event_count_before = OrderEvent.objects.filter(order=placed_order).count()

    response = client.post(
        _transition_url(placed_order.pk), {"to_status": "APPROVED"},
    )

    assert response.status_code == 200
    placed_order.refresh_from_db()
    assert placed_order.status == OrderStatus.APPROVED
    assert OrderEvent.objects.filter(order=placed_order).count() == event_count_before + 1

    latest = OrderEvent.objects.filter(order=placed_order).order_by("at").last()
    assert latest.from_status == "PLACED"
    assert latest.to_status == "APPROVED"
    assert latest.actor == admin_user


@pytest.mark.django_db
def test_invalid_transition_rejected(client, admin_user, placed_order):
    """PLACED -> READY is not in the ADMIN state table; must be rejected."""
    client.force_login(admin_user)

    response = client.post(
        _transition_url(placed_order.pk), {"to_status": "READY"},
    )

    assert response.status_code == 403
    placed_order.refresh_from_db()
    assert placed_order.status == OrderStatus.PLACED


@pytest.mark.django_db
def test_non_admin_gets_403(client, agent_user, placed_order):
    """An AGENT cannot use the admin transition endpoint."""
    client.force_login(agent_user)

    response = client.post(
        _transition_url(placed_order.pk), {"to_status": "APPROVED"},
    )

    assert response.status_code == 403
    placed_order.refresh_from_db()
    assert placed_order.status == OrderStatus.PLACED


@pytest.mark.django_db
def test_missing_order_returns_404(client, admin_user):
    """Transitioning a non-existent order returns 404."""
    client.force_login(admin_user)

    response = client.post(
        _transition_url(99999), {"to_status": "APPROVED"},
    )

    assert response.status_code == 404
