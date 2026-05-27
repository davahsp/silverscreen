import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cinema.models import (
    Order,
    OrderAddon,
    OrderCharge,
    OrderChannel,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Seat,
    ShowTime,
    Ticket,
    TicketStatus,
)
from cinema.services.ids import next_code, next_order_number

SERVICE_CHARGE_NAME = "Biaya Layanan"
SERVICE_CHARGE_PRICE = 5000
PAYMENT_EXPIRATION_SECONDS = 900


ACTIVE_TICKET_STATUSES = [TicketStatus.HELD, TicketStatus.CONFIRMED, TicketStatus.USED]


def unavailable_seat_ids(showtime):
    return set(
        Ticket.objects.filter(showtime=showtime, status__in=ACTIVE_TICKET_STATUSES)
        .values_list("seat_id", flat=True)
    )


def parse_addons(post_data):
    addons = []
    for key, value in post_data.items():
        if not key.startswith("product_"):
            continue
        try:
            product_id = int(key.replace("product_", ""))
            quantity = int(value or 0)
        except ValueError:
            continue
        if quantity > 0:
            addons.append((product_id, quantity))
    return addons


def calculate_total(showtime, seats, addons):
    total = showtime.price * len(seats) + SERVICE_CHARGE_PRICE
    products = Product.objects.in_bulk([product_id for product_id, _qty in addons])
    for product_id, quantity in addons:
        product = products.get(product_id)
        if product and product.is_active:
            total += product.price * quantity
    return total


def validate_seats(showtime, seat_ids):
    if not seat_ids:
        raise ValidationError("Pilih minimal satu kursi.")
    if len(seat_ids) > Order.MAX_TICKETS:
        raise ValidationError(f"Pilih maksimal {Order.MAX_TICKETS} kursi.")
    seats = list(Seat.objects.select_for_update().filter(id__in=seat_ids, studio=showtime.studio, is_active=True))
    if len(seats) != len(set(seat_ids)):
        raise ValidationError("Sebagian kursi tidak tersedia.")
    unavailable = unavailable_seat_ids(showtime)
    if unavailable.intersection({seat.id for seat in seats}):
        raise ValidationError("Kursi yang dipilih sudah tidak tersedia.")
    return seats


@transaction.atomic
def create_online_order(showtime_id, seat_ids, addons, customer=None):
    showtime = ShowTime.objects.select_for_update().select_related("movie", "studio").get(id=showtime_id)
    if not showtime.is_active or not showtime.movie.is_active or not showtime.studio.is_active:
        raise ValidationError("Showtime tidak tersedia untuk pemesanan.")
    seats = validate_seats(showtime, seat_ids)
    total = calculate_total(showtime, seats, addons)

    order = Order.objects.create(
        customer=customer,
        number=next_order_number(Order),
        channel=OrderChannel.ONLINE,
        status=OrderStatus.PENDING,
        total_amount=total,
    )
    for seat in seats:
        Ticket.objects.create(
            code=next_code(Ticket, "code", "TKT-", 6),
            order=order,
            showtime=showtime,
            seat=seat,
            status=TicketStatus.HELD,
        )

    _create_addons_and_charge(order, addons)

    payment = Payment.objects.create(
        internal_payment_id=next_code(Payment, "internal_payment_id", "PAY-INT-", 4),
        order=order,
        amount=total,
        status=PaymentStatus.UNPAID,
    )

    from stub_payment_gateway.services import issue_payment

    issued = issue_payment(
        amount=payment.amount,
        expiration_in=PAYMENT_EXPIRATION_SECONDS,
        internal_payment_id=payment.internal_payment_id,
        issued_at=payment.created_at,
    )
    payment.gateway_payment_id = issued.gateway_payment_id
    payment.payment_url = issued.payment_url
    payment.va_account = issued.va_account
    payment.expired_at = issued.expires_at
    payment.save(update_fields=["gateway_payment_id", "payment_url", "va_account", "expired_at"])
    return order


@transaction.atomic
def create_onsite_order(showtime_id, seat_ids, addons, customer=None):
    showtime = ShowTime.objects.select_for_update().select_related("movie", "studio").get(id=showtime_id)
    if not showtime.is_active or not showtime.movie.is_active or not showtime.studio.is_active:
        raise ValidationError("Showtime tidak tersedia untuk penjualan counter.")
    seats = validate_seats(showtime, seat_ids)
    total = calculate_total(showtime, seats, addons) - SERVICE_CHARGE_PRICE

    order = Order.objects.create(
        customer=customer,
        number=next_order_number(Order),
        channel=OrderChannel.ONSITE,
        status=OrderStatus.CONFIRMED,
        total_amount=total,
    )
    now = timezone.now()
    for seat in seats:
        Ticket.objects.create(
            code=next_code(Ticket, "code", "TKT-", 6),
            qr_identifier=uuid.uuid4(),
            order=order,
            showtime=showtime,
            seat=seat,
            status=TicketStatus.CONFIRMED,
        )
    _create_addons_and_charge(order, addons, include_service_charge=False)
    Payment.objects.create(
        internal_payment_id=next_code(Payment, "internal_payment_id", "PAY-INT-", 4),
        order=order,
        amount=total,
        status=PaymentStatus.PAID,
        paid_at=now,
    )
    return order


def _create_addons_and_charge(order, addons, include_service_charge=True):
    products = Product.objects.in_bulk([product_id for product_id, _qty in addons])
    for product_id, quantity in addons:
        product = products.get(product_id)
        if product and product.is_active and quantity > 0:
            OrderAddon.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price,
                total_price=product.price * quantity,
            )
    if include_service_charge:
        OrderCharge.objects.create(order=order, name=SERVICE_CHARGE_NAME, price=SERVICE_CHARGE_PRICE)
