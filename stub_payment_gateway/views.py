import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from cinema.services.payments import apply_payment_callback

from .models import GatewayPayment, GatewayPaymentStatus
from .services import issue_payment


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
                "expires_at": issued.expires_at.isoformat(),
            }
        )


class GatewayPaymentView(DetailView):
    model = GatewayPayment
    slug_field = "gateway_payment_id"
    slug_url_kwarg = "gateway_payment_id"
    template_name = "stub_payment_gateway/pay.html"
    context_object_name = "payment"


class GatewaySuccessView(View):
    def post(self, request, gateway_payment_id):
        gateway_payment = get_object_or_404(GatewayPayment, gateway_payment_id=gateway_payment_id)
        if gateway_payment.status == GatewayPaymentStatus.WAITING_PAYMENT:
            gateway_payment.status = GatewayPaymentStatus.PAID
            gateway_payment.save(update_fields=["status"])
            apply_payment_callback(
                {
                    "internal_payment_id": gateway_payment.internal_payment_id,
                    "gateway_payment_id": gateway_payment.gateway_payment_id,
                    "status": "PAID",
                    "paid_at": timezone.now().isoformat(),
                }
            )
        return redirect(reverse("stub_gateway:pay", args=[gateway_payment.gateway_payment_id]))


class GatewayExpireView(View):
    def post(self, request, gateway_payment_id):
        gateway_payment = get_object_or_404(GatewayPayment, gateway_payment_id=gateway_payment_id)
        if gateway_payment.status == GatewayPaymentStatus.WAITING_PAYMENT:
            gateway_payment.status = GatewayPaymentStatus.EXPIRED
            gateway_payment.expired_at = timezone.now()
            gateway_payment.save(update_fields=["status", "expired_at"])
            apply_payment_callback(
                {
                    "internal_payment_id": gateway_payment.internal_payment_id,
                    "gateway_payment_id": gateway_payment.gateway_payment_id,
                    "status": "EXPIRED",
                    "expired_at": gateway_payment.expired_at.isoformat(),
                }
            )
        return redirect(reverse("stub_gateway:pay", args=[gateway_payment.gateway_payment_id]))
