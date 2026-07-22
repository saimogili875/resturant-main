"""Views for customer delivery ordering and checkout.

Thin views orchestrating services.create_order() and build_maps_url().
Never computes pricing or mutates status directly.
"""
from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.core.ratelimits import checkout, messaging
from apps.menu.models import Category as MenuCategory
from apps.menu.models import MenuItem
from apps.menu.services import get_cached_menu
from apps.orders import services
from apps.orders.models import Order, OrderStatus
from apps.orders.services import build_maps_url, create_order

# Salt for the per-order signed tracking cookie set at checkout. Must match
# the value used when the cookie is written in delivery_checkout().
_TRACKING_SALT = "delv_tracking"


def _get_delivery_cart(session_dict: dict) -> tuple[list[dict], Decimal, int]:
    """Parse session delivery cart into item dicts and computed total."""
    cart_raw = session_dict.get("delv_cart", {})
    if not cart_raw:
        return [], Decimal("0"), 0

    item_ids = [int(mid) for mid in cart_raw.keys()]
    menu_items = {
        mi.pk: mi
        for mi in MenuItem.objects.filter(pk__in=item_ids, is_available=True)
    }

    cart_items = []
    total = Decimal("0")
    count = 0
    for mid_str, qty in cart_raw.items():
        mid = int(mid_str)
        if mid in menu_items and qty > 0:
            mi = menu_items[mid]
            line_tot = mi.effective_price * qty
            cart_items.append(
                {
                    "item": mi,
                    "quantity": qty,
                    "line_total": line_tot,
                }
            )
            total += line_tot
            count += qty
    return cart_items, total, count


@require_GET
def delivery_menu(request):
    """Render the public delivery menu with server-side cart."""
    all_categories = get_cached_menu()
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "all")

    if search or (category and category != "all"):
        item_qs = MenuItem.objects.filter(is_available=True).order_by("name")
        if search:
            item_qs = item_qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category and category != "all":
            item_qs = item_qs.filter(category__name=category)
        categories = MenuCategory.objects.filter(is_active=True).prefetch_related(
            Prefetch("items", queryset=item_qs)
        ).order_by("sort_order", "name")
    else:
        categories = all_categories

    has_results = any(len(cat.items.all()) > 0 for cat in categories)
    cart_items, cart_total, cart_count = _get_delivery_cart(request.session)

    context = {
        "categories": categories,
        "all_categories": all_categories,
        "has_results": has_results,
        "search": search,
        "category": category,
        "cart_items": cart_items,
        "cart_total": cart_total,
        "cart_count": cart_count,
    }
    if request.headers.get("HX-Request"):
        return render(request, "orders/customer/partials/menu_results.html", context)
    return render(request, "orders/customer/menu.html", context)


@require_POST
def cart_add(request):
    """HTMX endpoint to add a menu item to the delivery session cart."""
    menu_item_id = request.POST.get("menu_item_id")
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    error = None
    if menu_item_id and quantity > 0:
        mi = MenuItem.objects.filter(pk=menu_item_id).first()
        if not mi or not mi.is_available:
            error = f"'{mi.name if mi else menu_item_id}' is currently unavailable."
        elif not mi.is_orderable:
            error = f"'{mi.name}' is sold out."
        else:
            cart = request.session.get("delv_cart", {})
            current_qty = cart.get(str(menu_item_id), 0)
            if mi.track_stock and mi.stock_quantity < (current_qty + quantity):
                if mi.stock_quantity:
                    error = f"Only {mi.stock_quantity} left of '{mi.name}'."
                else:
                    error = f"'{mi.name}' is sold out."
            else:
                cart[str(menu_item_id)] = current_qty + quantity
                request.session["delv_cart"] = cart
                request.session.modified = True

    cart_items, cart_total, cart_count = _get_delivery_cart(request.session)
    context = {
        "cart_items": cart_items,
        "cart_total": cart_total,
        "cart_count": cart_count,
        "error": error,
    }
    return render(request, "orders/customer/partials/cart_bar.html", context)


@checkout
@require_http_methods(["GET", "POST"])
def delivery_checkout(request):
    """Render checkout form or process delivery order placement (COD)."""
    cart_items, cart_total, cart_count = _get_delivery_cart(request.session)

    if not cart_items:
        return redirect("orders_customer:menu")

    if request.method == "GET":
        context = {
            "cart_items": cart_items,
            "cart_total": cart_total,
            "cart_count": cart_count,
        }
        return render(request, "orders/customer/checkout.html", context)

    # POST checkout
    contact_name = request.POST.get("contact_name", "").strip()
    contact_phone = request.POST.get("contact_phone", "").strip()
    address = request.POST.get("address", "").strip()
    instructions = request.POST.get("instructions", "").strip()
    lat = request.POST.get("lat", "").strip()
    lng = request.POST.get("lng", "").strip()

    valid_lat = None
    valid_lng = None
    if lat and lng:
        try:
            f_lat = float(lat)
            f_lng = float(lng)
            if -90.0 <= f_lat <= 90.0 and -180.0 <= f_lng <= 180.0:
                valid_lat = lat
                valid_lng = lng
            else:
                lat = ""
                lng = ""
        except (ValueError, TypeError):
            lat = ""
            lng = ""
    else:
        lat = ""
        lng = ""

    errors = []
    if not contact_name:
        errors.append("Contact name is required.")
    if not contact_phone:
        errors.append("Contact phone number is required.")
    if not (valid_lat and valid_lng) and not address:
        errors.append("A delivery location is required (share your location or enter an address).")

    form_data = request.POST.copy()
    form_data["lat"] = lat
    form_data["lng"] = lng

    if errors:
        context = {
            "cart_items": cart_items,
            "cart_total": cart_total,
            "cart_count": cart_count,
            "errors": errors,
            "form_data": form_data,
        }
        return render(request, "orders/customer/checkout.html", context, status=400)

    if valid_lat and valid_lng:
        maps_url = build_maps_url(lat=valid_lat, lng=valid_lng)
    else:
        maps_url = build_maps_url(address=address)
    items = [
        {"menu_item_id": entry["item"].pk, "quantity": entry["quantity"]}
        for entry in cart_items
    ]

    customer = request.user if request.user.is_authenticated else None

    try:
        order = create_order(
            order_type="DELV",
            items=items,
            customer=customer,
            contact_name=contact_name,
            contact_phone=contact_phone,
            maps_url=maps_url,
            instructions=instructions,
        )
    except ValidationError as exc:
        context = {
            "cart_items": cart_items,
            "cart_total": cart_total,
            "cart_count": cart_count,
            "errors": exc.messages if hasattr(exc, "messages") else [str(exc)],
            "form_data": form_data,
        }
        return render(request, "orders/customer/checkout.html", context, status=400)

    # Clear delivery cart
    request.session["delv_cart"] = {}
    delv_orders = request.session.get("delv_orders", [])
    if order.pk not in delv_orders:
        delv_orders.append(order.pk)
    request.session["delv_orders"] = delv_orders
    request.session.modified = True

    response = render(request, "orders/customer/thank_you.html", {"order": order})
    response.set_signed_cookie(
        f"delv_token_{order.pk}", str(order.pk), salt=_TRACKING_SALT
    )
    return response


# ---------------------------------------------------------------------------
# Tracking + quick messaging (Task 6.5)
# ---------------------------------------------------------------------------

def _may_access_order(request, order: Order) -> bool:
    """Authorise viewing/messaging an order without a login (anti-IDOR).

    A guest proves ownership with the signed ``delv_token_<pk>`` cookie set
    at checkout — the ONLY way an anonymous visitor may reach the order.
    Logged-in staff also qualify: the assigned agent (so they can chat with
    the customer) and any ADMIN. Everyone else is treated as a stranger.
    """
    try:
        token = request.get_signed_cookie(
            f"delv_token_{order.pk}", salt=_TRACKING_SALT
        )
    except (KeyError, signing.BadSignature):
        token = None
    if token == str(order.pk):
        return True

    user = request.user
    return user.is_authenticated and (
        user.role == "ADMIN" or order.agent_id == user.pk
    )


@require_GET
def track_order(request, pk):
    """Guest-facing live tracking page for a single delivery order."""
    order = get_object_or_404(
        Order.objects.select_related("customer", "table", "agent", "session"),
        pk=pk,
    )
    if not _may_access_order(request, order):
        raise Http404("No such order.")

    context = {
        "order": order,
        "messages": order.messages.select_related("sender").all(),
        # Code -> human label map for the Alpine status ticker (safe JSON).
        "status_labels": dict(OrderStatus.choices),
    }
    return render(request, "orders/customer/track.html", context)


@messaging
@require_POST
def post_order_message(request, pk):
    """Post a short chat message on an order; return the rendered bubble."""
    order = get_object_or_404(
        Order.objects.select_related("customer", "table", "agent", "session"),
        pk=pk,
    )
    if not _may_access_order(request, order):
        raise Http404("No such order.")

    body = request.POST.get("body", "").strip()
    if not body:
        return HttpResponseBadRequest("Message cannot be empty.")

    sender = request.user if request.user.is_authenticated else None
    message = services.post_message(order, sender, body)
    return render(request, "orders/customer/partials/message.html", {"message": message})
