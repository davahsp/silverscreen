import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from cinema.models import OrderStatus, Payment, PaymentStatus, TicketStatus


@transaction.atomic
def apply_payment_callback(payload):
    status = payload.get("status")
    if status not in [PaymentStatus.PAID, PaymentStatus.EXPIRED]:
        raise ValidationError("Status callback tidak valid.")

    internal_payment_id = payload.get("internal_payment_id")
    gateway_payment_id = payload.get("gateway_payment_id")
    try:
        payment = Payment.objects.select_for_update().select_related("order").get(
            internal_payment_id=internal_payment_id
        )
    except Payment.DoesNotExist as exc:
        raise ValidationError("Payment tidak ditemukan.") from exc

    if payment.gateway_payment_id != gateway_payment_id:
        raise ValidationError("Gateway payment id tidak cocok.")
    if payload.get("va_account") and payment.va_account and payment.va_account != payload.get("va_account"):
        raise ValidationError("Virtual account tidak cocok.")
    if payment.status == status:
        return payment
    if payment.status not in [PaymentStatus.UNPAID]:
        raise ValidationError("Payment sudah berada pada status final.")

    order = payment.order
    if status == PaymentStatus.PAID:
        payment.status = PaymentStatus.PAID
        payment.paid_at = parse_datetime(payload.get("paid_at") or "") or None
        order.status = OrderStatus.CONFIRMED
        order.save(update_fields=["status"])
        for ticket in order.tickets.select_for_update().filter(status=TicketStatus.HELD):
            ticket.status = TicketStatus.CONFIRMED
            ticket.qr_identifier = uuid.uuid4()
            ticket.save(update_fields=["status", "qr_identifier"])
        payment.save(update_fields=["status", "paid_at"])
        return payment

    payment.status = PaymentStatus.EXPIRED
    payment.expired_at = parse_datetime(payload.get("expired_at") or "") or payment.expired_at
    order.status = OrderStatus.EXPIRED
    order.save(update_fields=["status"])
    order.tickets.filter(status=TicketStatus.HELD).update(status=TicketStatus.EXPIRED)
    payment.save(update_fields=["status", "expired_at"])
    return payment
