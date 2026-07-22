"""Tests for customer delivery ordering views."""
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.menu.models import Category, MenuItem
from apps.orders.models import Order


@pytest.fixture
def category(db):
    """A simple active menu category."""
    return Category.objects.create(name="Mains", is_active=True)


@pytest.fixture
def burger(category):
    """A menu item with a 20% discount: price=100, effective=80."""
    return MenuItem.objects.create(
        category=category,
        name="Burger",
        price=Decimal("100.00"),
        offer_percent=20,
        is_available=True,
    )


@pytest.mark.django_db
def test_delivery_menu_view(client, burger):
    """GET /order/menu/ renders the public delivery menu."""
    url = reverse("orders_customer:menu")
    response = client.get(url)
    assert response.status_code == 200
    assert burger.name in response.content.decode("utf-8")


@pytest.mark.django_db
def test_cart_add_view(client, burger):
    """POST /order/cart/add adds item to session cart and renders fragment."""
    url = reverse("orders_customer:cart_add")
    response = client.post(url, {"menu_item_id": burger.pk, "quantity": 2})
    assert response.status_code == 200
    assert "2 items" in response.content.decode("utf-8")
    assert client.session["delv_cart"][str(burger.pk)] == 2


@pytest.mark.django_db
def test_checkout_get_redirects_when_empty(client):
    """GET /order/checkout/ redirects to menu if cart is empty."""
    url = reverse("orders_customer:checkout")
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("orders_customer:menu")


@pytest.mark.django_db
def test_checkout_post_creates_order(client, burger):
    """POST /order/checkout/ creates a COD delivery order and stores signed cookie."""
    session = client.session
    session["delv_cart"] = {str(burger.pk): 1}
    session.save()

    url = reverse("orders_customer:checkout")
    payload = {
        "contact_name": "Alice Guest",
        "contact_phone": "555-0199",
        "address": "742 Evergreen Terrace",
        "instructions": "Leave on porch",
    }
    response = client.post(url, payload)
    assert response.status_code == 200
    assert "Order Placed Successfully" in response.content.decode("utf-8")

    order = Order.objects.get(contact_name="Alice Guest")
    assert order.order_type == "DELV"
    assert order.total_amount == Decimal("80.00")
    assert order.maps_url == "https://www.google.com/maps/dir/?api=1&destination=742%20Evergreen%20Terrace"
    assert f"delv_token_{order.pk}" in response.cookies


@pytest.mark.django_db
def test_checkout_post_with_valid_lat_lng_creates_order(client, burger):
    """checkout POST with valid lat/lng creates a DELV order with a coords-based maps_url."""
    session = client.session
    session["delv_cart"] = {str(burger.pk): 1}
    session.save()

    url = reverse("orders_customer:checkout")
    payload = {
        "contact_name": "Bob GPS",
        "contact_phone": "555-0200",
        "lat": "17.4065",
        "lng": "78.4772",
        "address": "",
    }
    response = client.post(url, payload)
    assert response.status_code == 200

    order = Order.objects.get(contact_name="Bob GPS")
    assert order.order_type == "DELV"
    assert order.maps_url == "https://www.google.com/maps/dir/?api=1&destination=17.4065,78.4772"


@pytest.mark.django_db
def test_checkout_post_missing_location_is_rejected(client, burger):
    """checkout POST with NEITHER lat/lng NOR address is REJECTED (no order created)."""
    session = client.session
    session["delv_cart"] = {str(burger.pk): 1}
    session.save()

    url = reverse("orders_customer:checkout")
    payload = {
        "contact_name": "No Location",
        "contact_phone": "555-0300",
        "address": "",
        "lat": "",
        "lng": "",
    }
    response = client.post(url, payload)
    assert response.status_code == 400
    content = response.content.decode("utf-8")
    assert "A delivery location is required" in content
    assert Order.objects.filter(contact_name="No Location").count() == 0


@pytest.mark.django_db
def test_checkout_post_invalid_lat_lng_ignored_and_rejected_if_no_address(client, burger):
    """invalid lat/lng (out of range/junk) is ignored; if no address either -> rejected."""
    session = client.session
    session["delv_cart"] = {str(burger.pk): 1}
    session.save()

    url = reverse("orders_customer:checkout")
    payload = {
        "contact_name": "Junk Coords",
        "contact_phone": "555-0400",
        "lat": "999.9",
        "lng": "invalid_lng",
        "address": "",
    }
    response = client.post(url, payload)
    assert response.status_code == 400
    content = response.content.decode("utf-8")
    assert "A delivery location is required" in content
    assert Order.objects.filter(contact_name="Junk Coords").count() == 0

