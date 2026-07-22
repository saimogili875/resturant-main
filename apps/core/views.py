"""Core views — infrastructure endpoints + public landing page."""
from django.http import JsonResponse
from django.shortcuts import render

from apps.menu.models import MenuItem


def healthz(request):
    """Liveness probe — returns 200 with {"status": "ok"}."""
    return JsonResponse({"status": "ok"})


def home(request):
    """Public RDH Cafe landing page served at "/".

    Pulls up to six available menu items for the "Menu Highlights" section.
    Falls back to curated sample dishes when the catalogue is empty so the
    section always renders. Purely presentational — no state is mutated.
    """
    highlights = list(
        MenuItem.objects.filter(is_available=True)
        .select_related("category")
        .order_by("category__sort_order", "name")[:6]
    )

    sample_dishes = [
        {"name": "Storm Smash Burger",
         "description": "Double patty, aged cheddar, house sauce", "price": "320"},
        {"name": "Thunder Wings",
         "description": "Slow-smoked, gold-chilli glaze", "price": "280"},
        {"name": "Midnight Mocha",
         "description": "Single-origin espresso, dark cocoa", "price": "180"},
        {"name": "Golden Hour Fries",
         "description": "Truffle salt, parmesan dust", "price": "160"},
        {"name": "Rudra Biryani",
         "description": "Dum-cooked, saffron, smoked raita", "price": "340"},
        {"name": "Eye of the Storm",
         "description": "Molten chocolate, gold leaf", "price": "220"},
    ]

    context = {
        "highlights": highlights,
        "sample_dishes": sample_dishes,
    }
    return render(request, "pages/home.html", context)
