from django.contrib.messages import get_messages

from .messages import serialize_messages


def toast_messages(request):
    if request.headers.get("HX-Request") == "true":
        return {"toast_messages": []}
    return {"toast_messages": serialize_messages(get_messages(request))}
