from django.contrib import admin

from .models import (
    Movie,
    MovieTheme,
    Order,
    OrderAddon,
    OrderCharge,
    Payment,
    Product,
    Seat,
    ShowTime,
    Studio,
    StudioType,
    Ticket,
)


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0


@admin.register(Studio)
class StudioAdmin(admin.ModelAdmin):
    list_display = ("name", "studio_type", "grid_rows", "grid_cols", "capacity", "is_active")
    inlines = [SeatInline]


@admin.register(ShowTime)
class ShowTimeAdmin(admin.ModelAdmin):
    list_display = ("movie", "studio", "start_at", "end_at", "price", "is_active")
    list_filter = ("is_active", "studio", "movie")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "channel", "status", "total_amount", "created_at")
    list_filter = ("channel", "status")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("internal_payment_id", "gateway_payment_id", "order", "amount", "status", "created_at")
    list_filter = ("status",)


admin.site.register(MovieTheme)
admin.site.register(Movie)
admin.site.register(StudioType)
admin.site.register(Product)
admin.site.register(Ticket)
admin.site.register(OrderAddon)
admin.site.register(OrderCharge)
