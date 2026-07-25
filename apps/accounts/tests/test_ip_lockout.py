"""Tests verifying that login lockout is scoped to (username, ip_address) pair."""
import pytest
from django.urls import reverse

from apps.accounts.models import LoginAttempt, User


@pytest.fixture
def agent_user():
    user = User.objects.create_user(username="testagent", password="correct_password", role="AGENT")
    return user


@pytest.mark.django_db
def test_ip_scoped_login_lockout(client, agent_user):
    """Failed login attempts from IP A do not lock out login attempts for the same user from IP B."""
    login_url = reverse("accounts:login")

    # Fail login 7 times from IP_A (192.168.1.100)
    for _ in range(7):
        client.post(
            login_url,
            {"username": "testagent", "password": "wrong_password"},
            REMOTE_ADDR="192.168.1.100",
        )

    # Assert IP_A is locked out
    res_a = client.post(
        login_url,
        {"username": "testagent", "password": "wrong_password"},
        REMOTE_ADDR="192.168.1.100",
    )
    assert b"Account locked" in res_a.content or b"Too many failed attempts" in res_a.content

    # Assert IP_B (192.168.1.200) can still attempt and log in with correct password
    res_b = client.post(
        login_url,
        {"username": "testagent", "password": "correct_password"},
        REMOTE_ADDR="192.168.1.200",
    )
    assert res_b.status_code == 302
    assert res_b.url == reverse("orders_agent:dashboard")
