from dataclasses import dataclass
from datetime import timedelta
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import GatewayPayment, GatewayPaymentStatus


@dataclass
class IssuedPayment:
    gateway_payment_id: str
    payment_url: str
    expired_in: int
    expires_at: object
    va_account: str


def next_gateway_id():
    count = GatewayPayment.objects.count() + 1
    value = f"PGW-{count:04d}"
    while GatewayPayment.objects.filter(gateway_payment_id=value).exists():
        count += 1
        value = f"PGW-{count:04d}"
    return value


def next_va_account():
    count = GatewayPayment.objects.count() + 1
    value = f"88080000{count:08d}"
    while GatewayPayment.objects.filter(va_account=value).exists():
        count += 1
        value = f"88080000{count:08d}"
    return value


def issue_payment(amount, expiration_in, internal_payment_id, issued_at=None, payment_api_key="mock-api-key"):
    issued_at = issued_at or timezone.now()
    expires_at = issued_at + timedelta(seconds=expiration_in)
    payment = GatewayPayment.objects.create(
        gateway_payment_id=next_gateway_id(),
        internal_payment_id=internal_payment_id,
        va_account=next_va_account(),
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
        expired_in=expiration_in,
        expires_at=expires_at,
        va_account=payment.va_account,
    )


def callback_url():
    return getattr(settings, "STUB_GATEWAY_CALLBACK_URL", "http://127.0.0.1:8000/payments/callback/")


def send_application_callback(payload):
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        callback_url(),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8") or "{}"
            return json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise ValidationError(f"Callback ditolak aplikasi: {body or exc.reason}") from exc
    except (URLError, TimeoutError) as exc:
        raise ValidationError(f"Callback aplikasi gagal: {exc}") from exc


def callback_payload(payment, status, occurred_at):
    payload = {
        "internal_payment_id": payment.internal_payment_id,
        "gateway_payment_id": payment.gateway_payment_id,
        "va_account": payment.va_account,
        "status": status,
    }
    if status == GatewayPaymentStatus.PAID:
        payload["paid_at"] = occurred_at.isoformat()
    elif status == GatewayPaymentStatus.EXPIRED:
        payload["expired_at"] = occurred_at.isoformat()
    return payload


def mark_paid(gateway_payment_id, paid_at=None, callback_sender=None):
    callback_sender = callback_sender or send_application_callback
    paid_at = paid_at or timezone.now()
    with transaction.atomic():
        payment = GatewayPayment.objects.select_for_update().get(gateway_payment_id=gateway_payment_id)
        if payment.status == GatewayPaymentStatus.PAID:
            return payment
        if payment.status != GatewayPaymentStatus.WAITING_PAYMENT:
            raise ValidationError("Payment gateway sudah berada pada status final.")
        payment.status = GatewayPaymentStatus.PAID
        payment.paid_at = paid_at
        payment.save(update_fields=["status", "paid_at"])
    callback_sender(callback_payload(payment, GatewayPaymentStatus.PAID, paid_at))
    return payment


def mark_expired(gateway_payment_id, expired_at=None, callback_sender=None):
    callback_sender = callback_sender or send_application_callback
    expired_at = expired_at or timezone.now()
    with transaction.atomic():
        payment = GatewayPayment.objects.select_for_update().get(gateway_payment_id=gateway_payment_id)
        if payment.status == GatewayPaymentStatus.EXPIRED:
            return payment
        if payment.status != GatewayPaymentStatus.WAITING_PAYMENT:
            raise ValidationError("Payment gateway sudah berada pada status final.")
        payment.status = GatewayPaymentStatus.EXPIRED
        payment.expired_at = expired_at
        payment.save(update_fields=["status", "expired_at"])
    callback_sender(callback_payload(payment, GatewayPaymentStatus.EXPIRED, expired_at))
    return payment


def mark_cancelled(gateway_payment_id):
    with transaction.atomic():
        payment = GatewayPayment.objects.select_for_update().get(gateway_payment_id=gateway_payment_id)
        if payment.status == GatewayPaymentStatus.CANCELLED:
            return payment
        if payment.status != GatewayPaymentStatus.WAITING_PAYMENT:
            raise ValidationError("Payment gateway sudah berada pada status final.")
        payment.status = GatewayPaymentStatus.CANCELLED
        payment.save(update_fields=["status"])
    return payment
