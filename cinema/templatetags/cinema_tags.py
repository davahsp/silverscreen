import base64
from io import BytesIO

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


@register.filter
def dict_get(mapping, key):
    if not mapping:
        return None
    return mapping.get(str(key), mapping.get(key))


@register.filter
def qr_svg_data_uri(value):
    if not value:
        return ""
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        return ""

    image = qrcode.make(str(value), image_factory=SvgPathImage, box_size=8, border=1)
    stream = BytesIO()
    image.save(stream)
    payload = base64.b64encode(stream.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"
