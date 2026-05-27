import time

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.utils import timezone

from stub_payment_gateway.models import GatewayPayment, GatewayPaymentStatus
from stub_payment_gateway.services import mark_expired


def expire_due_gateway_payments(stdout, now=None):
    now = now or timezone.now()
    payments = list(
        GatewayPayment.objects.filter(
            status=GatewayPaymentStatus.WAITING_PAYMENT,
            expired_at__lte=now,
        ).order_by("expired_at", "id")
    )
    expired_count = 0
    for payment in payments:
        try:
            mark_expired(payment.gateway_payment_id, expired_at=now)
        except ValidationError as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            stdout.write(f"FAILED {payment.gateway_payment_id}: {message}")
            continue
        expired_count += 1
        stdout.write(f"EXPIRED {payment.gateway_payment_id}")
    if not payments:
        stdout.write("No due gateway payments.")
    return expired_count


class Command(BaseCommand):
    help = "Expire due stub gateway payments and send callbacks to the application."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true", help="Keep checking for expired gateway payments.")
        parser.add_argument("--interval", type=int, default=5, help="Seconds between checks in watch mode.")

    def handle(self, *args, **options):
        if not options["watch"]:
            expire_due_gateway_payments(self.stdout)
            return

        interval = max(1, options["interval"])
        self.stdout.write(f"Watching gateway payments every {interval} seconds.")
        while True:
            expire_due_gateway_payments(self.stdout)
            time.sleep(interval)
