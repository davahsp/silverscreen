import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView

from .models import GatewayPayment
from .services import issue_payment, mark_expired, mark_paid


@method_decorator(csrf_exempt, name="dispatch")
class IssuePaymentView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            if payload.get("payment_api_key", "mock-api-key") != "mock-api-key":
                raise ValidationError("API key tidak valid.")
            issued = issue_payment(
                amount=int(payload["amount"]),
                expiration_in=int(payload.get("expiration_in", 900)),
                internal_payment_id=payload["internal_payment_id"],
                issued_at=timezone.now(),
            )
        except (KeyError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return JsonResponse({"ok": False, "error": message}, status=400)
        return JsonResponse(
            {
                "gateway_payment_id": issued.gateway_payment_id,
                "payment_url": issued.payment_url,
                "expired_in": issued.expired_in,
                "expires_at": issued.expires_at.isoformat(),
                "va_account": issued.va_account,
            }
        )


class GatewayPaymentListView(ListView):
    model = GatewayPayment
    template_name = "stub_payment_gateway/list.html"
    context_object_name = "payments"
    paginate_by = 30


class GatewayPaymentView(DetailView):
    model = GatewayPayment
    slug_field = "gateway_payment_id"
    slug_url_kwarg = "gateway_payment_id"
    template_name = "stub_payment_gateway/pay.html"
    context_object_name = "payment"


class GatewaySuccessView(View):
    def post(self, request, gateway_payment_id):
        gateway_payment = get_object_or_404(GatewayPayment, gateway_payment_id=gateway_payment_id)
        try:
            mark_paid(gateway_payment_id, paid_at=timezone.now())
        except ValidationError:
            pass
        return redirect(reverse("stub_gateway:pay", args=[gateway_payment.gateway_payment_id]))


class GatewayExpireView(View):
    def post(self, request, gateway_payment_id):
        gateway_payment = get_object_or_404(GatewayPayment, gateway_payment_id=gateway_payment_id)
        try:
            mark_expired(gateway_payment_id, expired_at=timezone.now())
        except ValidationError:
            pass
        return redirect(reverse("stub_gateway:pay", args=[gateway_payment.gateway_payment_id]))
