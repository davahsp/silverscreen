from django.core.exceptions import ValidationError
from django.db import transaction

from cinema.models import Order, OrderStatus, PaymentStatus, TicketStatus

USED_CANCEL_MESSAGE = "Tiket sudah digunakan, pesanan tidak dapat dibatalkan."


@transaction.atomic
def cancel_order(order_number):
    order = Order.objects.select_for_update().get(number=order_number)
    payment = order.payment
    tickets = order.tickets.select_for_update()
    if tickets.filter(status=TicketStatus.USED).exists():
        raise ValidationError(USED_CANCEL_MESSAGE)
    if payment.status == PaymentStatus.UNPAID:
        if payment.gateway_payment_id:
            from stub_payment_gateway.services import mark_cancelled

            mark_cancelled(payment.gateway_payment_id)
        order.status = OrderStatus.CANCELED
        payment.status = PaymentStatus.CANCELED_BEFORE_PAID
        tickets.update(status=TicketStatus.CANCELED)
        order.save(update_fields=["status"])
        payment.save(update_fields=["status"])
        return order
    if payment.status == PaymentStatus.PAID:
        order.status = OrderStatus.CANCELED
        payment.status = PaymentStatus.REFUND_PENDING
        tickets.update(status=TicketStatus.CANCELED)
        order.save(update_fields=["status"])
        payment.save(update_fields=["status"])
        return order
    raise ValidationError("Pesanan tidak dapat dibatalkan pada status saat ini.")


@transaction.atomic
def print_order_tickets(order_number):
    order = Order.objects.select_for_update().get(number=order_number)
    if order.status != OrderStatus.CONFIRMED:
        raise ValidationError("Hanya pesanan terkonfirmasi yang dapat dicetak.")
    return order
