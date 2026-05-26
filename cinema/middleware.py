import json

from django.contrib.messages import get_messages

from .messages import serialize_messages


HTMX_MESSAGES_EVENT = "ss:messages"


class HtmxMessageToastMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.headers.get("HX-Request") != "true":
            return response
        if 300 <= response.status_code < 400:
            return response

        messages = serialize_messages(get_messages(request))
        if not messages:
            return response

        trigger = self._get_trigger(response)
        trigger[HTMX_MESSAGES_EVENT] = {"messages": messages}
        response.headers["HX-Trigger"] = json.dumps(trigger)
        return response

    def _get_trigger(self, response):
        value = response.headers.get("HX-Trigger")
        if not value:
            return {}
        try:
            trigger = json.loads(value)
        except json.JSONDecodeError:
            return {value: None}
        if isinstance(trigger, str):
            return {trigger: None}
        if isinstance(trigger, dict):
            return trigger
        return {}
