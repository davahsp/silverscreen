from django import template

register = template.Library()


@register.filter
def rupiah(value):
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        value = 0
    return f"Rp{value:,.0f}".replace(",", ".")


@register.filter
def status_class(value):
    return str(value or "").lower()


@register.filter
def seat_status(occupancy, seat_id):
    return occupancy.get(seat_id)
