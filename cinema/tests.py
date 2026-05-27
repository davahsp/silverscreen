import json
from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.base import Message
from django.contrib.messages import constants as message_constants
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cinema.constants import BOOKING_WINDOW_DAYS
from cinema.messages import serialize_messages
from cinema.models import (
    AgeRating,
    Movie,
    MovieTheme,
    Order,
    OrderChannel,
    OrderStatus,
    PaymentStatus,
    Product,
    ProductCategory,
    Seat,
    ShowTime,
    Studio,
    StudioType,
    TicketStatus,
)
from cinema.services.booking import create_online_order, create_onsite_order
from cinema.services.cancellation import USED_CANCEL_MESSAGE, cancel_order, print_order_tickets
from cinema.services.payments import apply_payment_callback
from cinema.services.scheduling import disable_showtime, save_showtime
from cinema.services.studios import save_studio_layout
from stub_payment_gateway.management.commands.expire_gateway_payments import expire_due_gateway_payments
from stub_payment_gateway.models import GatewayPayment, GatewayPaymentStatus
from stub_payment_gateway.services import mark_paid


def make_role_user(username, role):
    user = User.objects.create_user(username=username, password=f"{username}-pass")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


class SilverScreenServiceTests(TestCase):
    def setUp(self):
        self.customer = make_role_user("customer1", "customer")
        self.client.force_login(self.customer)
        theme = MovieTheme.objects.create(name="Drama")
        self.movie = Movie.objects.create(
            title="Ruang Sunyi",
            synopsis="Drama musik.",
            age_rating=AgeRating.R13,
            runtime_minutes=112,
            movie_theme=theme,
        )
        self.inactive_movie = Movie.objects.create(
            title="Arsip Film Lama",
            synopsis="Dokumenter.",
            age_rating=AgeRating.R7,
            runtime_minutes=90,
            movie_theme=theme,
            is_active=False,
        )
        self.studio_type = StudioType.objects.create(name="Regular", base_price=45000)
        self.studio = Studio.objects.create(name="Studio 1", studio_type=self.studio_type, grid_rows=2, grid_cols=3)
        save_studio_layout(self.studio, {(0, 0), (0, 1), (1, 0)})
        self.seats = list(Seat.objects.filter(studio=self.studio).order_by("number"))
        self.showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now() + timedelta(days=1),
            price=45000,
        )
        self.product = Product.objects.create(name="Popcorn", price=30000, category=ProductCategory.FOOD)
        self.inactive_product = Product.objects.create(
            name="Legacy Snack",
            price=15000,
            category=ProductCategory.FOOD,
            is_active=False,
        )

    def test_online_order_creation_holds_seats_and_creates_unpaid_payment(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [(self.product.id, 2)])

        self.assertEqual(order.channel, OrderChannel.ONLINE)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.tickets.get().status, TicketStatus.HELD)
        self.assertEqual(order.payment.status, PaymentStatus.UNPAID)
        self.assertTrue(order.payment.gateway_payment_id)
        self.assertTrue(order.payment.payment_url)
        self.assertTrue(order.payment.va_account)

    def test_online_order_prevents_unavailable_seats(self):
        create_online_order(self.showtime.id, [self.seats[0].id], [])

        with self.assertRaises(ValidationError):
            create_online_order(self.showtime.id, [self.seats[0].id], [])

    def test_order_max_tickets_is_enforced_by_booking_service(self):
        studio = Studio.objects.create(
            name="Studio Besar",
            studio_type=self.studio_type,
            grid_rows=1,
            grid_cols=Order.MAX_TICKETS + 1,
        )
        save_studio_layout(studio, {(0, column) for column in range(Order.MAX_TICKETS + 1)})
        showtime = save_showtime(
            movie=self.movie,
            studio=studio,
            start_at=timezone.now() + timedelta(days=1, hours=4),
            price=45000,
        )
        seats = list(Seat.objects.filter(studio=studio).order_by("grid_x_pos"))

        with self.assertRaisesMessage(ValidationError, f"Pilih maksimal {Order.MAX_TICKETS} kursi."):
            create_online_order(showtime.id, [seat.id for seat in seats], [])

    def test_paid_callback_confirms_order_and_tickets(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        apply_payment_callback(
            {
                "internal_payment_id": order.payment.internal_payment_id,
                "gateway_payment_id": order.payment.gateway_payment_id,
                "status": "PAID",
                "paid_at": timezone.now().isoformat(),
            }
        )

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(order.payment.status, PaymentStatus.PAID)
        ticket = order.tickets.get()
        self.assertEqual(ticket.status, TicketStatus.CONFIRMED)
        self.assertIsNotNone(ticket.qr_identifier)

    def test_expired_callback_expires_order_and_releases_seat(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        apply_payment_callback(
            {
                "internal_payment_id": order.payment.internal_payment_id,
                "gateway_payment_id": order.payment.gateway_payment_id,
                "status": "EXPIRED",
                "expired_at": timezone.now().isoformat(),
            }
        )

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.EXPIRED)
        self.assertEqual(order.payment.status, PaymentStatus.EXPIRED)
        self.assertEqual(order.tickets.get().status, TicketStatus.EXPIRED)
        second = create_online_order(self.showtime.id, [self.seats[0].id], [])
        self.assertEqual(second.status, OrderStatus.PENDING)

    def test_callback_rejects_unknown_payment_and_invalid_status(self):
        with self.assertRaises(ValidationError):
            apply_payment_callback({"internal_payment_id": "NOPE", "gateway_payment_id": "PGW-X", "status": "PAID"})
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        with self.assertRaises(ValidationError):
            apply_payment_callback(
                {
                    "internal_payment_id": order.payment.internal_payment_id,
                    "gateway_payment_id": order.payment.gateway_payment_id,
                    "status": "BOGUS",
                }
            )

    def test_callback_rejects_mismatched_va_account(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        with self.assertRaisesMessage(ValidationError, "Virtual account tidak cocok."):
            apply_payment_callback(
                {
                    "internal_payment_id": order.payment.internal_payment_id,
                    "gateway_payment_id": order.payment.gateway_payment_id,
                    "va_account": "8808000099999999",
                    "status": "PAID",
                }
            )

    def test_issue_payment_endpoint_returns_va_and_expiration_info(self):
        response = self.client.post(
            reverse("stub_gateway:issue_payment"),
            data=json.dumps(
                {
                    "payment_api_key": "mock-api-key",
                    "amount": 125000,
                    "expiration_in": 120,
                    "internal_payment_id": "PAY-INT-9999",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["expired_in"], 120)
        self.assertTrue(payload["gateway_payment_id"])
        self.assertTrue(payload["payment_url"])
        self.assertTrue(payload["va_account"])
        self.assertTrue(GatewayPayment.objects.filter(va_account=payload["va_account"]).exists())

    def test_gateway_mark_paid_sends_application_callback_payload(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        gateway_payment = GatewayPayment.objects.get(gateway_payment_id=order.payment.gateway_payment_id)
        paid_at = timezone.now()

        with patch("stub_payment_gateway.services.send_application_callback") as sender:
            mark_paid(gateway_payment.gateway_payment_id, paid_at=paid_at)

        gateway_payment.refresh_from_db()
        self.assertEqual(gateway_payment.status, GatewayPaymentStatus.PAID)
        self.assertEqual(gateway_payment.paid_at, paid_at)
        payload = sender.call_args.args[0]
        self.assertEqual(payload["status"], "PAID")
        self.assertEqual(payload["internal_payment_id"], order.payment.internal_payment_id)
        self.assertEqual(payload["gateway_payment_id"], gateway_payment.gateway_payment_id)
        self.assertEqual(payload["va_account"], gateway_payment.va_account)
        self.assertEqual(payload["paid_at"], paid_at.isoformat())

    def test_gateway_expiration_worker_expires_due_gateway_payment_and_sends_callback(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        gateway_payment = GatewayPayment.objects.get(gateway_payment_id=order.payment.gateway_payment_id)
        now = timezone.now()
        gateway_payment.expired_at = now - timedelta(seconds=1)
        gateway_payment.save(update_fields=["expired_at"])
        output = StringIO()

        with patch("stub_payment_gateway.services.send_application_callback") as sender:
            expired_count = expire_due_gateway_payments(output, now=now)

        gateway_payment.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(gateway_payment.status, GatewayPaymentStatus.EXPIRED)
        self.assertIn(f"EXPIRED {gateway_payment.gateway_payment_id}", output.getvalue())
        self.assertEqual(sender.call_args.args[0]["status"], "EXPIRED")

    def test_unpaid_cancellation_sets_canceled_before_paid(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        gateway_payment = GatewayPayment.objects.get(gateway_payment_id=order.payment.gateway_payment_id)

        cancel_order(order.number)

        order.refresh_from_db()
        gateway_payment.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELED)
        self.assertEqual(order.payment.status, PaymentStatus.CANCELED_BEFORE_PAID)
        self.assertEqual(order.tickets.get().status, TicketStatus.CANCELED)
        self.assertEqual(gateway_payment.status, GatewayPaymentStatus.CANCELLED)

    def test_unpaid_cancellation_does_not_override_final_gateway_payment(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        GatewayPayment.objects.filter(gateway_payment_id=order.payment.gateway_payment_id).update(
            status=GatewayPaymentStatus.PAID,
            paid_at=timezone.now(),
        )

        with self.assertRaisesMessage(ValidationError, "Payment gateway sudah berada pada status final."):
            cancel_order(order.number)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment.status, PaymentStatus.UNPAID)
        self.assertEqual(order.tickets.get().status, TicketStatus.HELD)

    def test_paid_confirmed_cancellation_goes_to_refund_queue(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        apply_payment_callback(
            {
                "internal_payment_id": order.payment.internal_payment_id,
                "gateway_payment_id": order.payment.gateway_payment_id,
                "status": "PAID",
            }
        )

        cancel_order(order.number)

        order.refresh_from_db()
        self.assertEqual(order.payment.status, PaymentStatus.REFUND_PENDING)
        self.assertEqual(order.tickets.get().status, TicketStatus.CANCELED)

    def test_used_ticket_cancellation_is_blocked_and_keeps_qr_identifier(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [])
        ticket = order.tickets.get()
        qr_identifier = ticket.qr_identifier
        ticket.status = TicketStatus.USED
        ticket.save(update_fields=["status"])

        with self.assertRaisesMessage(ValidationError, USED_CANCEL_MESSAGE):
            cancel_order(order.number)

        ticket.refresh_from_db()
        self.assertEqual(ticket.qr_identifier, qr_identifier)

    def test_onsite_order_is_confirmed_paid_and_has_qr_without_pending(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [(self.product.id, 1)])

        self.assertEqual(order.channel, OrderChannel.ONSITE)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(order.payment.status, PaymentStatus.PAID)
        ticket = order.tickets.get()
        self.assertEqual(ticket.status, TicketStatus.CONFIRMED)
        self.assertIsNotNone(ticket.qr_identifier)

    def test_print_order_tickets_does_not_change_ticket_status_or_qr_identifier(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [])
        ticket = order.tickets.get()
        qr_identifier = ticket.qr_identifier

        print_order_tickets(order.number)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.CONFIRMED)
        self.assertEqual(ticket.qr_identifier, qr_identifier)

    def test_showtime_end_at_and_disable_rules(self):
        self.assertEqual(self.showtime.duration_minutes, self.movie.runtime_minutes)
        self.assertEqual(self.showtime.end_at, self.showtime.start_at + timedelta(minutes=self.movie.runtime_minutes))
        disable_showtime(self.showtime.id)
        self.showtime.refresh_from_db()
        self.assertFalse(self.showtime.is_active)

        active = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=self.showtime.end_at + timedelta(hours=1),
            price=45000,
        )
        create_online_order(active.id, [self.seats[0].id], [])
        with self.assertRaises(ValidationError):
            disable_showtime(active.id)

    def test_used_ticket_blocks_seat_resale_and_showtime_disable(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [])
        ticket = order.tickets.get()
        ticket.status = TicketStatus.USED
        ticket.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            create_online_order(self.showtime.id, [self.seats[0].id], [])
        with self.assertRaises(ValidationError):
            disable_showtime(self.showtime.id)

    def test_studio_capacity_and_zero_seat_validation(self):
        self.assertEqual(self.studio.capacity, 3)
        empty = Studio(name="Studio Empty", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        with self.assertRaises(ValidationError):
            save_studio_layout(empty, set())

    def test_inactive_movies_and_products_hidden_from_customer_pages(self):
        response = self.client.get(reverse("cinema:movies"))
        self.assertContains(response, self.movie.title)
        self.assertNotContains(response, self.inactive_movie.title)

        response = self.client.post(reverse("cinema:booking", args=[self.showtime.id]), {"seats": [self.seats[0].id]})
        self.assertRedirects(response, reverse("cinema:booking_addons", args=[self.showtime.id]))
        response = self.client.get(reverse("cinema:booking_addons", args=[self.showtime.id]))
        self.assertContains(response, "Pilih Kursi")
        self.assertContains(response, "Add-ons")
        self.assertContains(response, "Review")
        self.assertContains(response, "Pembayaran")
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, self.inactive_product.name)

    def test_movie_index_only_shows_movies_with_active_showtimes_in_booking_window(self):
        future_movie = Movie.objects.create(
            title="Film Bulan Depan",
            synopsis="Belum dapat dipesan.",
            age_rating=AgeRating.R13,
            runtime_minutes=95,
            movie_theme=self.movie.movie_theme,
        )
        no_showtime_movie = Movie.objects.create(
            title="Film Tanpa Jadwal",
            synopsis="Tidak memiliki showtime.",
            age_rating=AgeRating.R13,
            runtime_minutes=95,
            movie_theme=self.movie.movie_theme,
        )
        save_showtime(
            movie=future_movie,
            studio=self.studio,
            start_at=timezone.now() + timedelta(days=BOOKING_WINDOW_DAYS + 1),
            price=45000,
        )

        response = self.client.get(reverse("cinema:movies"))

        self.assertContains(response, self.movie.title)
        self.assertNotContains(response, future_movie.title)
        self.assertNotContains(response, no_showtime_movie.title)

    def test_movie_detail_paginates_showtimes_by_day_inside_booking_window(self):
        second_studio = Studio.objects.create(name="Studio 2", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(second_studio, {(0, 0)})
        selected_start = timezone.now() + timedelta(days=2, hours=3)
        selected_showtime = save_showtime(
            movie=self.movie,
            studio=second_studio,
            start_at=selected_start,
            price=50000,
        )
        selected_date = timezone.localtime(selected_showtime.start_at).date().isoformat()

        response = self.client.get(reverse("cinema:movie_detail", args=[self.movie.id]), {"date": selected_date})

        self.assertContains(response, "Studio 2")
        self.assertContains(response, "Rp50.000")
        self.assertNotContains(response, "Studio 1")
        self.assertContains(response, f'value="{selected_date}"')
        self.assertContains(response, 'hx-include="#showtime-date-filter"')

    def test_movie_detail_htmx_replaces_showtime_list_for_selected_day(self):
        second_studio = Studio.objects.create(name="Studio 2", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(second_studio, {(0, 0)})
        selected_showtime = save_showtime(
            movie=self.movie,
            studio=second_studio,
            start_at=timezone.now() + timedelta(days=2, hours=3),
            price=50000,
        )
        selected_date = timezone.localtime(selected_showtime.start_at).date().isoformat()

        response = self.client.get(
            reverse("cinema:movie_detail", args=[self.movie.id]),
            {"date": selected_date},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, 'id="showtime-list"')
        self.assertContains(response, "Studio 2")
        self.assertNotContains(response, "Studio 1")
        self.assertNotContains(response, 'id="showtime-date-filter"')
        self.assertNotContains(response, "hx-push-url")
        self.assertNotContains(response, 'hx-trigger="load"')
        self.assertNotContains(response, "<!doctype html>")
        self.assertNotContains(response, "Sinopsis")

    def test_full_page_messages_are_serialized_for_toasts(self):
        response = self.client.post(reverse("cinema:booking", args=[self.showtime.id]), {"seats": []})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "django-messages-data")
        self.assertContains(response, f"Pilih 1 sampai {Order.MAX_TICKETS} kursi.")

    def test_booking_seat_page_uses_order_max_tickets(self):
        response = self.client.get(reverse("cinema:booking", args=[self.showtime.id]))

        self.assertEqual(response.context["max_ticket_quantity"], Order.MAX_TICKETS)
        self.assertContains(response, f"const maxSeats = {Order.MAX_TICKETS};")
        self.assertContains(
            response,
            f"Anda hanya bisa membeli maksimal {Order.MAX_TICKETS} tiket dalam satu pesanan",
        )
        self.assertContains(response, "data-seat-selectable")
        self.assertContains(response, "legend-available")
        self.assertContains(response, "legend-selected")
        self.assertContains(response, "legend-taken")
        self.assertContains(response, "Sudah Diambil")
        self.assertNotContains(response, "legend-disabled")
        self.assertNotContains(response, "Nonaktif")

    def test_payment_pages_show_unpaid_va_instruction_without_gateway_ids(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        for url in [
            reverse("cinema:booking_payment", args=[order.number]),
            reverse("cinema:order_detail", args=[order.number]),
        ]:
            response = self.client.get(url)
            self.assertContains(response, "Transfer tepat sebesar")
            self.assertContains(response, order.payment.va_account)
            self.assertContains(response, "Sisa Waktu")
            self.assertContains(response, "data-countdown")
            self.assertNotContains(response, "Internal Payment")
            self.assertNotContains(response, "Internal ID")
            self.assertNotContains(response, "Gateway Payment")
            self.assertNotContains(response, "Gateway ID")
            self.assertNotContains(response, "Expired")
            self.assertNotContains(response, "QR Identifier")

    def test_order_list_cards_link_to_order_detail_and_show_movie_summary(self):
        self.movie.main_picture = "/static/posters/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])
        order = create_online_order(self.showtime.id, [self.seats[0].id, self.seats[1].id], [])

        response = self.client.get(reverse("cinema:orders"))

        detail_url = reverse("cinema:order_detail", args=[order.number])
        self.assertContains(response, "Metode Pemesanan")
        self.assertNotContains(response, "Sumber")
        self.assertNotContains(response, ">Detail<")
        self.assertContains(response, f'class="order-list-card" href="{detail_url}"')
        self.assertContains(response, self.movie.main_picture)
        self.assertContains(response, self.movie.title)
        self.assertContains(response, "2 tiket")
        self.assertContains(response, timezone.localtime(self.showtime.start_at).strftime("%H:%M"))
        self.assertContains(response, order.get_channel_display())

    def test_final_payment_pages_hide_va_instruction_and_countdown(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        apply_payment_callback(
            {
                "internal_payment_id": order.payment.internal_payment_id,
                "gateway_payment_id": order.payment.gateway_payment_id,
                "status": "PAID",
                "paid_at": timezone.now().isoformat(),
            }
        )
        order.refresh_from_db()

        response = self.client.get(reverse("cinema:order_detail", args=[order.number]))
        self.assertContains(response, "Dibayar pada")
        self.assertContains(response, "data:image/svg+xml;base64")
        self.assertNotContains(response, "QR Identifier")
        self.assertNotContains(response, str(order.tickets.get().qr_identifier))
        self.assertNotContains(response, "Transfer tepat sebesar")
        self.assertNotContains(response, "Sisa Waktu")
        self.assertNotContains(response, "data-countdown")
        self.assertNotContains(response, "Expired")

    def test_htmx_messages_are_sent_in_trigger_header(self):
        response = self.client.post(
            reverse("cinema:booking", args=[self.showtime.id]),
            {"seats": []},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        trigger = json.loads(response.headers["HX-Trigger"])
        self.assertEqual(
            trigger["ss:messages"]["messages"][0]["message"],
            f"Pilih 1 sampai {Order.MAX_TICKETS} kursi.",
        )
        self.assertIn("error", trigger["ss:messages"]["messages"][0]["tags"])

    def test_htmx_messages_are_consumed_after_trigger_header(self):
        message_text = f"Pilih 1 sampai {Order.MAX_TICKETS} kursi."
        self.client.post(
            reverse("cinema:booking", args=[self.showtime.id]),
            {"seats": []},
            headers={"HX-Request": "true"},
        )

        response = self.client.get(reverse("cinema:movies"))

        self.assertNotContains(response, message_text)

    def test_htmx_redirect_preserves_messages_for_followup_response(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        response = self.client.post(
            reverse("cinema:order_cancel", args=[order.number]),
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("HX-Trigger", response.headers)

        response = self.client.get(response.headers["Location"], headers={"HX-Request": "true"})
        trigger = json.loads(response.headers["HX-Trigger"])
        self.assertEqual(trigger["ss:messages"]["messages"][0]["message"], "Pesanan dibatalkan.")


class MessageSerializationTests(TestCase):
    def test_message_level_and_tags_survive_serialization(self):
        serialized = serialize_messages(
            [Message(message_constants.ERROR, "Tidak valid.", extra_tags="booking")]
        )

        self.assertEqual(serialized[0]["message"], "Tidak valid.")
        self.assertEqual(serialized[0]["level"], message_constants.ERROR)
        self.assertIn("booking", serialized[0]["tags"])
        self.assertIn("error", serialized[0]["tags"])


class AuthenticationTests(TestCase):
    def setUp(self):
        theme = MovieTheme.objects.create(name="Drama")
        self.movie = Movie.objects.create(
            title="Ruang Sunyi",
            synopsis="Drama musik.",
            age_rating=AgeRating.R13,
            runtime_minutes=112,
            movie_theme=theme,
        )
        self.studio_type = StudioType.objects.create(name="Regular", base_price=45000)
        self.studio = Studio.objects.create(
            name="Studio 1", studio_type=self.studio_type, grid_rows=1, grid_cols=1
        )
        from cinema.services.studios import save_studio_layout
        from cinema.services.scheduling import save_showtime
        save_studio_layout(self.studio, {(0, 0)})
        self.showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now() + timedelta(days=1),
            price=45000,
        )

    def test_movies_list_is_public(self):
        response = self.client.get(reverse("cinema:movies"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masuk")
        self.assertContains(response, "Daftar")

    def test_movie_detail_is_public(self):
        response = self.client.get(reverse("cinema:movie_detail", args=[self.movie.id]))
        self.assertEqual(response.status_code, 200)

    def test_booking_requires_login(self):
        response = self.client.get(reverse("cinema:booking", args=[self.showtime.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("cinema:login"), response.headers["Location"])

    def test_navigation_marks_exact_customer_target_active(self):
        customer = make_role_user("nav_customer", "customer")
        self.client.force_login(customer)

        response = self.client.get(reverse("cinema:movies"))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Pilih Film"])
        self.assertEqual(response.context["navigation_items"][0]["url"], reverse("cinema:movies"))

    def test_navigation_marks_parent_target_active_for_sub_view(self):
        manager = make_role_user("nav_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_movie_edit", args=[self.movie.id]))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Film"])

    def test_navigation_exact_match_wins_over_parent_sub_match(self):
        scheduler = make_role_user("nav_scheduler", "scheduler")
        self.client.force_login(scheduler)

        response = self.client.get(reverse("cinema:scheduler_showtime_new"))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Jadwalkan"])

    def test_login_redirects_customer_to_movies(self):
        make_role_user("alice", "customer")
        response = self.client.post(
            reverse("cinema:login"),
            {"username": "alice", "password": "alice-pass"},
        )
        self.assertRedirects(response, reverse("cinema:movies"))

    def test_login_redirects_manager_to_dashboard(self):
        make_role_user("bob", "manager")
        response = self.client.post(
            reverse("cinema:login"),
            {"username": "bob", "password": "bob-pass"},
        )
        self.assertRedirects(response, reverse("cinema:manager_dashboard"))

    def test_role_mismatch_is_blocked_and_redirected(self):
        customer = make_role_user("c1", "customer")
        self.client.force_login(customer)
        response = self.client.get(reverse("cinema:manager_dashboard"))
        self.assertRedirects(response, reverse("cinema:movies"))

    def test_signup_creates_customer_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse("cinema:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Sup3rSecret!",
                "password2": "Sup3rSecret!",
            },
        )
        self.assertRedirects(response, reverse("cinema:login"))
        user = User.objects.get(username="newuser")
        self.assertTrue(user.groups.filter(name="customer").exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_redirects_to_login(self):
        user = make_role_user("c2", "customer")
        self.client.force_login(user)
        response = self.client.post(reverse("cinema:logout"))
        self.assertRedirects(response, reverse("cinema:login"))
