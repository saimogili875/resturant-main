"""Tests for services.assign_agent — admin forwards a delivery to an agent."""
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role, User
from apps.accounts.services import set_agent_availability
from apps.menu.models import Category, MenuItem
from apps.orders.services import assign_agent, create_order


@pytest.fixture
def burger(db):
    """A basic available menu item."""
    category = Category.objects.create(name="Mains", is_active=True)
    return MenuItem.objects.create(
        category=category,
        name="Burger",
        price=Decimal("50.00"),
        is_available=True,
    )


@pytest.fixture
def admin_user(db):
    """A user with the ADMIN role."""
    return User.objects.create_user(username="admin_a", password="pw", role=Role.ADMIN)


@pytest.fixture
def available_agent(db):
    """An AGENT whose AgentProfile is marked available."""
    agent = User.objects.create_user(username="agent_a", password="pw", role=Role.AGENT)
    set_agent_availability(agent, available=True)
    return agent


@pytest.fixture
def delivery_order(burger):
    """A freshly placed delivery order awaiting an agent."""
    return create_order(
        order_type="DELV",
        items=[{"menu_item_id": burger.pk, "quantity": 1}],
    )


@pytest.mark.django_db
def test_assign_available_agent_sets_agent_and_writes_event(
    delivery_order, available_agent, admin_user
):
    """Assigning an available agent sets order.agent and logs an audit event."""
    status_before = delivery_order.status
    event_count_before = delivery_order.events.count()

    updated = assign_agent(delivery_order, available_agent, admin_user)

    assert updated.agent == available_agent
    updated.refresh_from_db()
    assert updated.agent_id == available_agent.pk
    # Status is unchanged; the event just records the assignment.
    assert updated.status == status_before
    assert updated.events.count() == event_count_before + 1
    latest = updated.events.order_by("at").last()
    assert latest.from_status == status_before
    assert latest.to_status == status_before
    assert latest.actor == admin_user


@pytest.mark.django_db
def test_assign_unavailable_agent_raises(delivery_order, admin_user):
    """An agent who is not available cannot be assigned."""
    busy_agent = User.objects.create_user(
        username="busy_a", password="pw", role=Role.AGENT
    )
    set_agent_availability(busy_agent, available=False)

    with pytest.raises(PermissionDenied):
        assign_agent(delivery_order, busy_agent, admin_user)

    delivery_order.refresh_from_db()
    assert delivery_order.agent_id is None


@pytest.mark.django_db
def test_assign_non_agent_raises(delivery_order, admin_user):
    """A user without the AGENT role cannot be assigned a delivery."""
    customer = User.objects.create_user(
        username="cust_a", password="pw", role=Role.CUSTOMER
    )

    with pytest.raises(PermissionDenied):
        assign_agent(delivery_order, customer, admin_user)


@pytest.mark.django_db
def test_assign_requires_admin_actor(delivery_order, available_agent):
    """Only an ADMIN may perform the assignment."""
    not_admin = User.objects.create_user(
        username="agent_b", password="pw", role=Role.AGENT
    )

    with pytest.raises(PermissionDenied):
        assign_agent(delivery_order, available_agent, not_admin)

    delivery_order.refresh_from_db()
    assert delivery_order.agent_id is None
