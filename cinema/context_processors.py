from django.contrib.messages import get_messages

from .messages import serialize_messages
from .navigation import ROLE_LABELS, build_navigation, user_role


def toast_messages(request):
    if request.headers.get("HX-Request") == "true":
        return {"toast_messages": []}
    return {"toast_messages": serialize_messages(get_messages(request))}


def navigation(request):
    role = user_role(getattr(request, "user", None))
    match = getattr(request, "resolver_match", None)
    current_view_name = getattr(match, "view_name", "") if match else ""
    return {
        "current_role": role,
        "current_role_label": ROLE_LABELS.get(role),
        "role_labels": ROLE_LABELS,
        "navigation_items": build_navigation(role, current_view_name),
    }
