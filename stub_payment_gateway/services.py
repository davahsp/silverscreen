from dataclasses import dataclass
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import GatewayPayment, GatewayPaymentStatus


@dataclass
class IssuedPayment:
    gateway_payment_id: str
    payment_url: str
    expires_at: object


def next_gateway_id():
    count = GatewayPayment.objects.count() + 1
    value = f"PGW-{count:04d}"
    while GatewayPayment.objects.filter(gateway_payment_id=value).exists():
        count += 1
        value = f"PGW-{count:04d}"
    return value


def issue_payment(amount, expiration_in, internal_payment_id, issued_at=None, payment_api_key="mock-api-key"):
    issued_at = issued_at or timezone.now()
    expires_at = issued_at + timedelta(seconds=expiration_in)
    payment = GatewayPayment.objects.create(
        gateway_payment_id=next_gateway_id(),
        internal_payment_id=internal_payment_id,
        client_id="SILVERSCREEN",
        amount=amount,
        issued_at=issued_at,
        expiration_in=expiration_in,
        expired_at=expires_at,
        status=GatewayPaymentStatus.WAITING_PAYMENT,
    )
    return IssuedPayment(
        gateway_payment_id=payment.gateway_payment_id,
        payment_url=reverse("stub_gateway:pay", args=[payment.gateway_payment_id]),
        expires_at=expires_at,
    )
