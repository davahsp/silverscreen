from django.db import models
from django.utils import timezone


class GatewayPaymentStatus(models.TextChoices):
    WAITING_PAYMENT = "WAITING_PAYMENT", "Menunggu Bayar"
    PAID = "PAID", "Paid"
    EXPIRED = "EXPIRED", "Expired"


class GatewayPayment(models.Model):
    gateway_payment_id = models.CharField(max_length=32, unique=True)
    internal_payment_id = models.CharField(max_length=32)
    client_id = models.CharField(max_length=80, default="SILVERSCREEN")
    amount = models.PositiveIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    expiration_in = models.PositiveIntegerField(default=900)
    expired_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=GatewayPaymentStatus.choices,
        default=GatewayPaymentStatus.WAITING_PAYMENT,
    )

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return self.gateway_payment_id
