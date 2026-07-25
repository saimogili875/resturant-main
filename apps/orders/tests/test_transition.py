"""Tests for services.transition — role enforcement and audit events."""
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Role, User
from apps.accounts.services import set_agent_availability
from apps.menu.models import Category, MenuItem
from apps.orders.models import OrderStatus
from apps.orders.services import assign_agent, create_order, transition



@pytest.fixture
def category(db):
    """A simple active menu category."""
    return Category.objects.create(name="Mains", is_active=True)


@pytest.fixture
def burger(category):
    """A basic available menu item."""
    return MenuItem.objects.create(
        category=category,
        name="Burger",
        price=Decimal("50.00"),
        is_available=True,
    )


@pytest.fixture
def admin_user(db):
    """A user with the ADMIN role."""
    return User.objects.create_user(
        username="admin_t", password="pw", role=Role.ADMIN
    )


@pytest.fixture
def agent_user(db):
    """A user with the AGENT role."""
    return User.objects.create_user(
        username="agent_t", password="pw", role=Role.AGENT
    )


@pytest.fixture
def placed_order(burger):
    """A freshly placed delivery order."""
    return create_order(
        order_type="DELV",
        items=[{"menu_item_id": burger.pk, "quantity": 1}],
    )


@pytest.mark.django_db
def test_transition_allowed_updates_status(placed_order, admin_user):
    """An allowed transition updates the order status."""
    updated = transition(placed_order, "APPROVED", admin_user)
    assert updated.status == OrderStatus.APPROVED


@pytest.mark.django_db
def test_transition_allowed_appends_event(placed_order, admin_user):
    """An allowed transition appends an OrderEvent."""
    transition(placed_order, "APPROVED", admin_user)

    # Should now have 2 events: initial PLACED + APPROVED
    events = list(placed_order.events.order_by("at"))
    assert len(events) == 2
    latest = events[-1]
    assert latest.from_status == OrderStatus.PLACED
    assert latest.to_status == OrderStatus.APPROVED
    assert latest.actor == admin_user


@pytest.mark.django_db
def test_transition_disallowed_raises(placed_order, agent_user):
    """A disallowed transition raises PermissionDenied."""
    with pytest.raises(PermissionDenied):
        transition(placed_order, "APPROVED", agent_user)


@pytest.mark.django_db
def test_transition_disallowed_no_side_effects(
    placed_order, agent_user
):
    """A disallowed transition leaves status and events unchanged."""
    initial_event_count = placed_order.events.count()

    with pytest.raises(PermissionDenied):
        transition(placed_order, "APPROVED", agent_user)

    placed_order.refresh_from_db()
    assert placed_order.status == OrderStatus.PLACED
    assert placed_order.events.count() == initial_event_count


@pytest.mark.django_db
def test_transition_dispatch_requires_assigned_agent(
    placed_order, admin_user, agent_user
):
    """Transitioning to DISPATCH raises ValidationError if order.agent is None, and succeeds after assignment."""
    set_agent_availability(agent_user, available=True)
    transition(placed_order, OrderStatus.APPROVED, admin_user)
    transition(placed_order, OrderStatus.IN_KITCHEN, admin_user)
    transition(placed_order, OrderStatus.READY, admin_user)

    assert placed_order.agent_id is None
    with pytest.raises(ValidationError, match="Assign a delivery agent before dispatching."):
        transition(placed_order, OrderStatus.DISPATCHED, admin_user)

    assign_agent(placed_order, agent_user, admin_user)
    updated = transition(placed_order, OrderStatus.DISPATCHED, admin_user)
    assert updated.status == OrderStatus.DISPATCHED

