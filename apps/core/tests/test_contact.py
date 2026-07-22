import pytest
from django.core import mail
from django.urls import reverse

from apps.core.forms import ContactForm


@pytest.mark.django_db
def test_contact_page_get(client):
    url = reverse("contact")
    response = client.get(url)
    assert response.status_code == 200
    assert "form" in response.context
    assert isinstance(response.context["form"], ContactForm)


@pytest.mark.django_db
def test_contact_page_post_success(client):
    url = reverse("contact")
    data = {
        "name": "Test User",
        "email": "testuser@example.com",
        "message": "Hello, this is a test message for Cafe Rudra!",
    }
    response = client.post(url, data)
    assert response.status_code == 200

    # Verify email was sent
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert "New Contact Message from Test User" in sent_email.subject
    assert "testuser@example.com" in sent_email.body
    assert "Hello, this is a test message for Cafe Rudra!" in sent_email.body
    assert "caferudrahyd@gmail.com" in sent_email.to
