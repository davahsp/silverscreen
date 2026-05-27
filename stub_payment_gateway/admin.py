from django.contrib import admin

from .models import GatewayPayment


@admin.register(GatewayPayment)
class GatewayPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "gateway_payment_id",
        "internal_payment_id",
        "va_account",
        "client_id",
        "amount",
        "status",
        "issued_at",
        "expired_at",
        "paid_at",
    )
    list_filter = ("status", "client_id")
