import json
import os
import tempfile
from io import BytesIO, StringIO
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.base import Message
from django.contrib.messages import constants as message_constants
from django.test import RequestFactory, TestCase, override_settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from PIL import Image

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
from cinema.views import RoleRequiredMixin
from stub_payment_gateway.management.commands.expire_gateway_payments import expire_due_gateway_payments
from stub_payment_gateway.models import GatewayPayment, GatewayPaymentStatus
from stub_payment_gateway.services import mark_paid


def make_role_user(username, role):
    user = User.objects.create_user(username=username, password=f"{username}-pass")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


def make_uploaded_image(filename, image_format, content_type):
    image = Image.new("RGB", (1, 1), "white")
    content = BytesIO()
    image.save(content, format=image_format)
    content.seek(0)
    return SimpleUploadedFile(filename, content.read(), content_type=content_type)


class SilverScreenServiceTests(TestCase):
    def setUp(self):
        self.customer = make_role_user("customer1", "customer")
        self.customer.email = "customer1@example.com"
        self.customer.save(update_fields=["email"])
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

    def test_role_required_mixin_accepts_string_or_multiple_allowed_roles(self):
        class StaffOnlyView(RoleRequiredMixin, View):
            allowed_roles = "staff"

            def get(self, request):
                return HttpResponse("ok")

        class StaffOrManagerView(RoleRequiredMixin, View):
            allowed_roles = ["staff", "manager"]

            def get(self, request):
                return HttpResponse("ok")

        factory = RequestFactory()
        staff = make_role_user("role_guard_staff", "staff")
        manager = make_role_user("role_guard_manager", "manager")

        staff_request = factory.get("/staff-only/")
        staff_request.user = staff
        self.assertEqual(StaffOnlyView.as_view()(staff_request).status_code, 200)

        for path, user in (("/multi-role/staff/", staff), ("/multi-role/manager/", manager)):
            request = factory.get(path)
            request.user = user
            self.assertEqual(StaffOrManagerView.as_view()(request).status_code, 200)

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

    def test_order_is_cancellable_flag_requires_online_pending_or_confirmed_without_used_tickets(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])
        self.assertTrue(order.is_cancellable)

        apply_payment_callback(
            {
                "internal_payment_id": order.payment.internal_payment_id,
                "gateway_payment_id": order.payment.gateway_payment_id,
                "status": "PAID",
            }
        )
        order.refresh_from_db()
        self.assertTrue(order.is_cancellable)

        order.status = OrderStatus.CANCELED
        order.save(update_fields=["status"])
        self.assertFalse(order.is_cancellable)

        expired_order = create_online_order(self.showtime.id, [self.seats[1].id], [])
        expired_order.status = OrderStatus.EXPIRED
        expired_order.save(update_fields=["status"])
        self.assertFalse(expired_order.is_cancellable)

        used_order = create_onsite_order(self.showtime.id, [self.seats[2].id], [])
        self.assertFalse(used_order.is_cancellable)
        ticket = used_order.tickets.get()
        ticket.status = TicketStatus.USED
        ticket.save(update_fields=["status"])
        self.assertFalse(used_order.is_cancellable)

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

    def test_onsite_order_cancellation_is_blocked(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [])

        with self.assertRaisesMessage(ValidationError, "Pesanan tidak dapat dibatalkan pada status saat ini."):
            cancel_order(order.number)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(order.payment.status, PaymentStatus.PAID)
        self.assertEqual(order.tickets.get().status, TicketStatus.CONFIRMED)

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
        self.assertIsNone(order.customer)
        ticket = order.tickets.get()
        self.assertEqual(ticket.status, TicketStatus.CONFIRMED)
        self.assertIsNotNone(ticket.qr_identifier)

    def test_pos_initial_page_has_unselected_showtime_carousel_without_seat_map(self):
        staff = make_role_user("counter_staff", "staff")
        self.client.force_login(staff)
        today_showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now() + timedelta(minutes=5),
            price=45000,
        )

        response = self.client.get(reverse("cinema:counter_pos"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["max_ticket_quantity"], Order.MAX_TICKETS)
        self.assertContains(response, 'data-showtime-carousel')
        self.assertContains(response, 'data-showtime-input')
        self.assertContains(response, 'type="radio"')
        self.assertContains(response, "Pelanggan (opsional)")
        self.assertContains(response, "Walk-in / tanpa akun")
        self.assertContains(response, "role=\"combobox\"")
        self.assertContains(response, "data-customer-search")
        self.assertContains(response, "data-customer-value")
        self.assertContains(response, "data-customer-dropdown")
        self.assertContains(response, "data-customer-option")
        self.assertContains(response, "data-customer-label")
        self.assertContains(response, "pos-customer-options")
        self.assertContains(response, self.customer.username)
        self.assertContains(response, self.customer.email)
        self.assertContains(response, f"const maxSeats = {Order.MAX_TICKETS};")
        self.assertContains(
            response,
            f"Anda hanya bisa membeli maksimal {Order.MAX_TICKETS} tiket dalam satu pesanan",
        )
        self.assertNotContains(response, '<select id="pos-showtime"')
        self.assertNotContains(response, '<select id="pos-customer"')
        self.assertNotContains(response, "<datalist")
        self.assertNotContains(response, " checked")
        self.assertContains(response, 'data-pos-order-area hidden')
        self.assertContains(response, f'value="{today_showtime.id}"')
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, f"Pilih Kursi - {self.movie.title}")

    def test_pos_htmx_showtime_change_returns_only_seat_map_partial(self):
        staff = make_role_user("counter_staff_htmx", "staff")
        self.client.force_login(staff)
        today_showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now(),
            price=45000,
        )

        response = self.client.get(
            reverse("cinema:counter_pos"),
            {"showtime": today_showtime.id},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Pilih Kursi - {self.movie.title}")
        self.assertContains(response, self.seats[0].number)
        self.assertContains(response, "data-seat-selectable")
        self.assertContains(response, "Sudah Diambil")
        self.assertNotContains(response, "<!doctype html>")
        self.assertNotContains(response, "Add-ons")

    def test_pos_can_assign_optional_customer_to_onsite_order(self):
        staff = make_role_user("counter_staff_customer", "staff")
        self.client.force_login(staff)
        today_showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now(),
            price=45000,
        )

        response = self.client.post(
            reverse("cinema:counter_pos"),
            {
                "showtime": today_showtime.id,
                "customer": self.customer.id,
                "seats": [self.seats[0].id],
            },
        )

        order = Order.objects.get(channel=OrderChannel.ONSITE)
        self.assertRedirects(response, reverse("cinema:order_detail", args=[order.number]))
        self.assertEqual(order.customer, self.customer)

    def test_pos_showtime_carousel_only_lists_today_showtimes_that_have_not_ended(self):
        staff = make_role_user("counter_staff_today", "staff")
        self.client.force_login(staff)
        today_showtime = save_showtime(
            movie=self.movie,
            studio=self.studio,
            start_at=timezone.now(),
            price=45000,
        )
        second_studio = Studio.objects.create(name="Studio 2", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(second_studio, {(0, 0)})
        tomorrow_showtime = save_showtime(
            movie=self.movie,
            studio=second_studio,
            start_at=timezone.now() + timedelta(days=1),
            price=45000,
        )
        third_studio = Studio.objects.create(name="Studio 3", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(third_studio, {(0, 0)})
        ended_start_at = timezone.now() - timedelta(minutes=self.movie.runtime_minutes + 5)
        ended_showtime = ShowTime.objects.create(
            movie=self.movie,
            studio=third_studio,
            start_at=ended_start_at,
            duration_minutes=self.movie.runtime_minutes,
            end_at=ended_start_at + timedelta(minutes=self.movie.runtime_minutes),
            price=45000,
        )

        response = self.client.get(reverse("cinema:counter_pos"))

        self.assertContains(response, f'value="{today_showtime.id}"')
        self.assertNotContains(response, f'value="{tomorrow_showtime.id}"')
        self.assertNotContains(response, f'value="{ended_showtime.id}"')

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

    def test_showtime_save_rejects_past_start_at(self):
        with self.assertRaisesMessage(ValidationError, "Jam mulai tidak boleh lebih awal dari waktu saat ini."):
            save_showtime(
                movie=self.movie,
                studio=self.studio,
                start_at=timezone.now() - timedelta(minutes=1),
                price=45000,
            )

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

    def test_movie_index_prefers_main_picture_before_fallback(self):
        self.movie.main_picture = "images/movies/main-pictures/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])

        response = self.client.get(reverse("cinema:movies"))

        self.assertContains(response, f'src="{self.movie.main_picture.url}"')
        self.assertContains(response, 'class="movie-poster-image"')
        self.assertNotContains(response, 'class="movie-poster-genre">Drama')

    def test_movie_detail_prefers_main_picture_before_fallback(self):
        self.movie.main_picture = "images/movies/main-pictures/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])

        response = self.client.get(reverse("cinema:movie_detail", args=[self.movie.id]))

        self.assertContains(response, f'src="{self.movie.main_picture.url}"')
        self.assertContains(response, 'class="movie-poster-image"')
        self.assertNotContains(response, 'class="movie-poster-title">Ruang Sunyi')

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

    def test_order_detail_cancel_button_uses_cancellable_flag(self):
        online_order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)
        onsite_order = create_onsite_order(self.showtime.id, [self.seats[1].id], [], customer=self.customer)

        response = self.client.get(reverse("cinema:order_detail", args=[online_order.number]))
        self.assertContains(response, "Batalkan Pesanan")
        self.assertContains(response, reverse("cinema:order_cancel", args=[online_order.pk]))

        response = self.client.get(reverse("cinema:order_detail", args=[onsite_order.number]))
        self.assertNotContains(response, "Batalkan Pesanan")
        self.assertNotContains(response, reverse("cinema:order_cancel", args=[onsite_order.pk]))

    def test_order_list_cards_link_to_order_detail_and_show_movie_summary(self):
        self.movie.main_picture = "images/movies/main-pictures/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])
        order = create_online_order(self.showtime.id, [self.seats[0].id, self.seats[1].id], [], customer=self.customer)

        response = self.client.get(reverse("cinema:orders"))

        self.assertContains(response, "Pesanan Saya")
        self.assertContains(response, 'id="order-filter"')
        self.assertContains(response, 'hx-get="/orders/table/"')
        self.assertContains(response, 'hx-target="#order-table-partial"')
        self.assertContains(response, 'hx-trigger="load"')
        self.assertContains(response, 'name="order_id"')
        self.assertContains(response, 'name="movie_name"')
        self.assertContains(response, 'type="date"')
        self.assertNotContains(response, f'class="order-list-card" href="{reverse("cinema:order_detail", args=[order.number])}"')

        response = self.client.get(reverse("cinema:orders_table"), headers={"HX-Request": "true"})

        detail_url = reverse("cinema:order_detail", args=[order.number])
        self.assertContains(response, "Metode Pemesanan")
        self.assertNotContains(response, "Sumber")
        self.assertNotContains(response, ">Detail<")
        self.assertContains(response, f'class="order-list-card" href="{detail_url}"')
        self.assertContains(response, self.movie.main_picture.url)
        self.assertContains(response, self.movie.title)
        self.assertContains(response, "2 tiket")
        self.assertContains(response, timezone.localtime(self.showtime.start_at).strftime("%H:%M"))
        self.assertContains(response, order.get_channel_display())
        self.assertNotContains(response, 'id="order-filter"')

    def test_order_table_partial_filters_by_order_id_movie_name_and_showtime_date(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)
        second_theme = MovieTheme.objects.create(name="Action")
        second_movie = Movie.objects.create(
            title="Langit Merah",
            synopsis="Aksi.",
            age_rating=AgeRating.R13,
            runtime_minutes=101,
            movie_theme=second_theme,
        )
        second_studio = Studio.objects.create(name="Studio 2", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(second_studio, {(0, 0)})
        second_showtime = save_showtime(
            movie=second_movie,
            studio=second_studio,
            start_at=timezone.now() + timedelta(days=3),
            price=45000,
        )
        second_seat = Seat.objects.get(studio=second_studio)
        second_order = create_online_order(second_showtime.id, [second_seat.id], [], customer=self.customer)

        response = self.client.get(reverse("cinema:orders_table"), {"order_id": order.number[-6:]})

        self.assertContains(response, order.number)
        self.assertNotContains(response, second_order.number)

        response = self.client.get(reverse("cinema:orders_table"), {"movie_name": second_movie.title[:6]})

        self.assertContains(response, second_order.number)
        self.assertNotContains(response, order.number)

        selected_date = timezone.localtime(second_showtime.start_at).date().isoformat()
        response = self.client.get(reverse("cinema:orders_table"), {"date": selected_date})

        self.assertContains(response, second_order.number)
        self.assertNotContains(response, order.number)

    def test_shared_orders_page_filters_customer_but_lists_all_orders_for_staff(self):
        online_order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)
        onsite_order = create_onsite_order(self.showtime.id, [self.seats[1].id], [(self.product.id, 1)])
        other_customer = make_role_user("orders_customer", "customer")
        second_studio = Studio.objects.create(name="Studio 2", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        save_studio_layout(second_studio, {(0, 0)})
        other_showtime = save_showtime(
            movie=self.movie,
            studio=second_studio,
            start_at=timezone.now() + timedelta(days=2),
            price=45000,
        )
        other_seat = Seat.objects.get(studio=second_studio)
        other_order = create_online_order(other_showtime.id, [other_seat.id], [], customer=other_customer)

        response = self.client.get(reverse("cinema:orders"))

        self.assertContains(response, "Pesanan Saya")
        self.assertContains(response, 'id="order-filter"')
        self.assertContains(response, 'name="order_id"')
        self.assertContains(response, 'name="movie_name"')
        self.assertContains(response, 'name="date"')
        self.assertNotContains(response, online_order.number)

        response = self.client.get(reverse("cinema:orders_table"), headers={"HX-Request": "true"})

        self.assertContains(response, online_order.number)
        self.assertNotContains(response, onsite_order.number)
        self.assertNotContains(response, other_order.number)

        staff = make_role_user("orders_staff", "staff")
        self.client.force_login(staff)

        response = self.client.get(reverse("cinema:orders"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daftar Pesanan")
        self.assertContains(response, 'id="order-filter"')
        self.assertNotContains(response, online_order.number)

        response = self.client.get(reverse("cinema:orders_table"), headers={"HX-Request": "true"})

        self.assertContains(response, f'class="order-list-card" href="{reverse("cinema:order_detail", args=[online_order.number])}"')
        self.assertContains(response, f'class="order-list-card" href="{reverse("cinema:order_detail", args=[onsite_order.number])}"')
        self.assertContains(response, f'class="order-list-card" href="{reverse("cinema:order_detail", args=[other_order.number])}"')
        self.assertContains(response, online_order.number)
        self.assertContains(response, onsite_order.number)
        self.assertContains(response, other_order.number)
        self.assertContains(response, "Metode Pemesanan")
        self.assertNotContains(response, 'id="order-filter"')
        self.assertNotContains(response, 'name="q"')

    def test_staff_orders_legacy_url_redirects_to_shared_orders_endpoint(self):
        staff = make_role_user("orders_staff_redirect", "staff")
        self.client.force_login(staff)

        response = self.client.get(reverse("cinema:order_lookup"))

        self.assertRedirects(response, reverse("cinema:orders"))

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

    def test_customer_cannot_cancel_another_customers_order(self):
        other_customer = make_role_user("cancel_other_customer", "customer")
        order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=other_customer)

        response = self.client.post(reverse("cinema:order_cancel", args=[order.pk]))

        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment.status, PaymentStatus.UNPAID)

    def test_staff_can_cancel_any_customer_order(self):
        staff = make_role_user("cancel_staff", "staff")
        self.client.force_login(staff)
        order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)

        response = self.client.post(reverse("cinema:order_cancel", args=[order.pk]))

        self.assertRedirects(response, reverse("cinema:order_detail", args=[order.number]))
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELED)
        self.assertEqual(order.payment.status, PaymentStatus.CANCELED_BEFORE_PAID)

    def test_scheduler_cannot_cancel_order(self):
        scheduler = make_role_user("cancel_scheduler", "scheduler")
        self.client.force_login(scheduler)
        order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)

        response = self.client.post(reverse("cinema:order_cancel", args=[order.pk]))

        self.assertRedirects(response, reverse("cinema:scheduler_showtimes"))
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)

    def test_htmx_redirect_preserves_messages_for_followup_response(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [], customer=self.customer)

        response = self.client.post(
            reverse("cinema:order_cancel", args=[order.pk]),
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

    def test_movies_route_uses_movies_path(self):
        self.assertEqual(reverse("cinema:movies"), "/movies/")

    def test_index_redirects_anonymous_user_to_movies(self):
        response = self.client.get(reverse("cinema:index"))

        self.assertRedirects(response, reverse("cinema:movies"))

    def test_index_redirects_authenticated_roles_to_default_pages(self):
        cases = [
            ("customer", "cinema:movies"),
            ("staff", "cinema:counter_pos"),
            ("scheduler", "cinema:scheduler_showtimes"),
            ("manager", "cinema:manager_dashboard"),
        ]

        for role, target in cases:
            with self.subTest(role=role):
                self.client.force_login(make_role_user(f"index_{role}", role))
                response = self.client.get(reverse("cinema:index"))
                self.assertRedirects(response, reverse(target), fetch_redirect_response=False)
                self.client.logout()

    def test_movie_detail_is_public(self):
        response = self.client.get(reverse("cinema:movie_detail", args=[self.movie.id]))
        self.assertEqual(response.status_code, 200)

    def test_booking_requires_login(self):
        response = self.client.get(reverse("cinema:booking", args=[self.showtime.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("cinema:login"), response.headers["Location"])

    def test_booking_seat_map_preserves_studio_layout_gaps(self):
        customer = make_role_user("seatmap_customer", "customer")
        self.client.force_login(customer)
        studio = Studio.objects.create(name="Seatmap Studio", studio_type=self.studio_type, grid_rows=2, grid_cols=3)
        save_studio_layout(studio, {(0, 0), (0, 2), (1, 1)})
        showtime = save_showtime(
            movie=self.movie,
            studio=studio,
            start_at=timezone.now() + timedelta(days=2),
            price=45000,
        )

        response = self.client.get(reverse("cinema:booking", args=[showtime.id]))

        self.assertContains(response, 'class="seat-grid seat-grid-actual"')
        self.assertContains(response, 'style="--studio-seat-cols: 3;"')
        self.assertContains(response, 'class="seat-map-empty-cell"', count=3)

    def test_pos_seat_map_preserves_studio_layout_gaps(self):
        staff = make_role_user("seatmap_staff", "staff")
        self.client.force_login(staff)
        studio = Studio.objects.create(name="POS Seatmap Studio", studio_type=self.studio_type, grid_rows=2, grid_cols=3)
        save_studio_layout(studio, {(0, 0), (0, 2), (1, 1)})
        showtime = save_showtime(
            movie=self.movie,
            studio=studio,
            start_at=timezone.now() + timedelta(minutes=5),
            price=45000,
        )

        response = self.client.get(reverse("cinema:counter_pos"), {"showtime": showtime.id})

        self.assertContains(response, 'class="seat-grid seat-grid-actual"')
        self.assertContains(response, 'style="--studio-seat-cols: 3;"')
        self.assertContains(response, 'class="seat-map-empty-cell"', count=3)

    def test_navigation_marks_exact_customer_target_active(self):
        customer = make_role_user("nav_customer", "customer")
        self.client.force_login(customer)

        response = self.client.get(reverse("cinema:movies"))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Pilih Film"])
        self.assertEqual(response.context["navigation_items"][0]["url"], reverse("cinema:movies"))
        self.assertContains(response, f'class="topbar-logo" href="{reverse("cinema:index")}"')

    def test_navigation_marks_parent_target_active_for_sub_view(self):
        manager = make_role_user("nav_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_movie_detail", args=[self.movie.id]))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Film"])

    def test_manager_movies_rows_link_to_detail_and_use_switch_for_active_toggle(self):
        manager = make_role_user("movie_switch_manager", "manager")
        self.client.force_login(manager)
        self.movie.main_picture = "images/movies/main-pictures/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])

        response = self.client.get(reverse("cinema:manager_movies"))

        self.assertContains(response, reverse("cinema:manager_movie_detail", args=[self.movie.id]))
        self.assertContains(response, "manager-movie-link")
        self.assertContains(response, self.movie.main_picture.url)
        self.assertNotContains(response, ">Edit</a>")
        self.assertContains(response, 'class="toggle-switch-input"')
        self.assertContains(response, 'role="switch"')
        self.assertContains(response, reverse("cinema:manager_movie_toggle", args=[self.movie.id]))

    def test_manager_movie_detail_shell_loads_htmx_partial(self):
        manager = make_role_user("movie_detail_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_movie_detail", args=[self.movie.id]))

        self.assertContains(response, 'id="manager-movie-detail"')
        self.assertContains(response, reverse("cinema:manager_movie_detail_partial", args=[self.movie.id]))
        self.assertContains(response, 'hx-trigger="load"')
        self.assertContains(response, 'hx-swap="outerHTML"')

    def test_manager_movie_create_uses_movie_form_layout(self):
        manager = make_role_user("movie_create_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_movie_new"))

        self.assertContains(response, "Tambah Film")
        self.assertContains(response, 'data-image-widget')
        self.assertContains(response, 'class="choice-pool"', count=2)
        self.assertNotContains(response, '<select name="movie_theme"')
        self.assertContains(response, 'type="hidden" name="is_active" value="on"')
        self.assertNotContains(response, 'role="switch"')
        self.assertContains(response, "manager-detail-synopsis-field")
        self.assertContains(response, "sticky-form-actions")
        self.assertNotContains(response, "Form Data")

    def test_manager_movie_detail_partial_switches_between_detail_and_update_modes(self):
        manager = make_role_user("movie_partial_manager", "manager")
        self.client.force_login(manager)

        detail_response = self.client.get(reverse("cinema:manager_movie_detail_partial", args=[self.movie.id]))
        update_response = self.client.get(
            reverse("cinema:manager_movie_detail_partial", args=[self.movie.id]),
            {"mode": "update"},
        )

        self.assertContains(detail_response, 'id="manager-movie-detail"')
        self.assertContains(detail_response, "?mode=update")
        self.assertContains(update_response, reverse("cinema:manager_movie_edit", args=[self.movie.id]))
        self.assertContains(update_response, 'hx-target="#manager-movie-detail"')
        self.assertContains(update_response, 'class="choice-pool"')
        self.assertContains(update_response, 'type="radio"')
        self.assertNotContains(update_response, '<select name="age_rating"')
        self.assertNotContains(update_response, '<select name="movie_theme"')
        self.assertNotContains(update_response, 'name="age_rating" value=""')
        self.assertContains(update_response, 'data-image-widget')
        self.assertContains(update_response, "None")
        self.assertContains(update_response, "Pilih Gambar")
        self.assertNotContains(update_response, "Currently")

    def test_manager_movie_image_widget_shows_bound_filename_and_preview(self):
        manager = make_role_user("movie_image_widget_manager", "manager")
        self.client.force_login(manager)
        self.movie.main_picture = f"images/movies/main-pictures/{self.movie.id}.png"
        self.movie.save(update_fields=["main_picture"])

        response = self.client.get(
            reverse("cinema:manager_movie_detail_partial", args=[self.movie.id]),
            {"mode": "update"},
        )

        self.assertContains(response, 'data-image-widget')
        self.assertContains(response, f"{self.movie.id}.png")
        self.assertContains(response, self.movie.main_picture.url)
        self.assertContains(response, 'data-image-widget-clear-input')
        self.assertContains(response, "Ganti Gambar")

    def test_manager_movie_main_picture_upload_replaces_previous_extension(self):
        manager = make_role_user("movie_upload_manager", "manager")
        self.client.force_login(manager)

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                form_data = {
                    "title": self.movie.title,
                    "synopsis": self.movie.synopsis,
                    "age_rating": self.movie.age_rating,
                    "runtime_minutes": self.movie.runtime_minutes,
                    "movie_theme": self.movie.movie_theme_id,
                    "is_active": "on",
                }
                first_image = make_uploaded_image("poster.gif", "GIF", "image/gif")
                response = self.client.post(
                    reverse("cinema:manager_movie_edit", args=[self.movie.id]),
                    {**form_data, "main_picture": first_image},
                )
                self.assertRedirects(response, reverse("cinema:manager_movie_detail", args=[self.movie.id]))
                self.movie.refresh_from_db()
                first_name = self.movie.main_picture.name
                self.assertTrue(first_name.endswith(f"/{self.movie.id}.gif"))
                self.assertTrue(os.path.exists(os.path.join(media_root, first_name)))

                second_image = make_uploaded_image("poster.png", "PNG", "image/png")
                response = self.client.post(
                    reverse("cinema:manager_movie_edit", args=[self.movie.id]),
                    {**form_data, "main_picture": second_image},
                )
                self.assertRedirects(response, reverse("cinema:manager_movie_detail", args=[self.movie.id]))
                self.movie.refresh_from_db()

                self.assertTrue(self.movie.main_picture.name.endswith(f"/{self.movie.id}.png"))
                self.assertFalse(os.path.exists(os.path.join(media_root, first_name)))
                self.assertTrue(os.path.exists(os.path.join(media_root, self.movie.main_picture.name)))

                second_name = self.movie.main_picture.name
                ignored_replacement = make_uploaded_image("ignored.gif", "GIF", "image/gif")
                response = self.client.post(
                    reverse("cinema:manager_movie_edit", args=[self.movie.id]),
                    {**form_data, "main_picture": ignored_replacement, "main_picture-clear": "on"},
                )
                self.assertRedirects(response, reverse("cinema:manager_movie_detail", args=[self.movie.id]))
                self.movie.refresh_from_db()

                self.assertFalse(self.movie.main_picture)
                self.assertFalse(os.path.exists(os.path.join(media_root, second_name)))

    def test_manager_products_rows_link_to_detail_and_use_square_image_switch(self):
        manager = make_role_user("product_switch_manager", "manager")
        self.client.force_login(manager)
        product = Product.objects.create(
            name="Caramel Popcorn",
            price=35000,
            category=ProductCategory.FOOD,
            picture="images/products/pictures/popcorn.png",
        )

        response = self.client.get(reverse("cinema:manager_products"))

        self.assertContains(response, reverse("cinema:manager_product_detail", args=[product.id]))
        self.assertContains(response, "manager-product-link")
        self.assertContains(response, product.picture.url)
        self.assertNotContains(response, ">Edit</a>")
        self.assertContains(response, 'class="toggle-switch-input"')
        self.assertContains(response, 'role="switch"')

    def test_manager_product_create_uses_product_form_layout(self):
        manager = make_role_user("product_create_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_product_new"))

        self.assertContains(response, "Tambah Produk")
        self.assertContains(response, 'data-image-widget')
        self.assertContains(response, "manager-product-media-widget")
        self.assertContains(response, 'class="choice-pool"')
        self.assertNotContains(response, '<select name="category"')
        self.assertContains(response, 'type="hidden" name="is_active" value="on"')
        self.assertNotContains(response, 'role="switch"')
        self.assertContains(response, "sticky-form-actions")

    def test_manager_product_detail_shell_and_partial_switch_modes(self):
        manager = make_role_user("product_detail_manager", "manager")
        self.client.force_login(manager)
        product = Product.objects.create(name="Iced Tea", price=18000, category=ProductCategory.DRINK)

        shell_response = self.client.get(reverse("cinema:manager_product_detail", args=[product.id]))
        detail_response = self.client.get(reverse("cinema:manager_product_detail_partial", args=[product.id]))
        update_response = self.client.get(
            reverse("cinema:manager_product_detail_partial", args=[product.id]),
            {"mode": "update"},
        )

        self.assertContains(shell_response, 'id="manager-product-detail"')
        self.assertContains(shell_response, reverse("cinema:manager_product_detail_partial", args=[product.id]))
        self.assertContains(detail_response, "?mode=update")
        self.assertContains(update_response, reverse("cinema:manager_product_edit", args=[product.id]))
        self.assertContains(update_response, 'hx-target="#manager-product-detail"')
        self.assertContains(update_response, "manager-product-media-widget")
        self.assertContains(update_response, 'class="choice-pool"')
        self.assertNotContains(update_response, '<select name="category"')
        self.assertContains(update_response, 'role="switch"')

    def test_manager_product_picture_upload_replaces_previous_extension(self):
        manager = make_role_user("product_upload_manager", "manager")
        self.client.force_login(manager)
        product = Product.objects.create(name="Nachos", price=42000, category=ProductCategory.FOOD)

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                form_data = {
                    "name": product.name,
                    "price": product.price,
                    "category": product.category,
                    "is_active": "on",
                }
                first_image = make_uploaded_image("nachos.gif", "GIF", "image/gif")
                response = self.client.post(
                    reverse("cinema:manager_product_edit", args=[product.id]),
                    {**form_data, "picture": first_image},
                )
                self.assertRedirects(response, reverse("cinema:manager_product_detail", args=[product.id]))
                product.refresh_from_db()
                first_name = product.picture.name
                self.assertTrue(first_name.endswith(f"/{product.id}.gif"))
                self.assertTrue(os.path.exists(os.path.join(media_root, first_name)))

                second_image = make_uploaded_image("nachos.png", "PNG", "image/png")
                response = self.client.post(
                    reverse("cinema:manager_product_edit", args=[product.id]),
                    {**form_data, "picture": second_image},
                )
                self.assertRedirects(response, reverse("cinema:manager_product_detail", args=[product.id]))
                product.refresh_from_db()

                self.assertTrue(product.picture.name.endswith(f"/{product.id}.png"))
                self.assertFalse(os.path.exists(os.path.join(media_root, first_name)))
                self.assertTrue(os.path.exists(os.path.join(media_root, product.picture.name)))

                second_name = product.picture.name
                ignored_replacement = make_uploaded_image("ignored.gif", "GIF", "image/gif")
                response = self.client.post(
                    reverse("cinema:manager_product_edit", args=[product.id]),
                    {**form_data, "picture": ignored_replacement, "picture-clear": "on"},
                )
                self.assertRedirects(response, reverse("cinema:manager_product_detail", args=[product.id]))
                product.refresh_from_db()

                self.assertFalse(product.picture)
                self.assertFalse(os.path.exists(os.path.join(media_root, second_name)))

    def test_manager_studio_create_uses_seatmap_builder(self):
        manager = make_role_user("studio_create_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_studio_new"))

        self.assertContains(response, "Tambah Studio")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'class="choice-pool"')
        self.assertContains(response, 'type="radio"')
        self.assertContains(response, 'data-studio-layout')
        self.assertContains(response, 'name="layout_rows" value="10"')
        self.assertContains(response, 'name="layout_cols" value="15"')
        self.assertContains(response, 'data-layout-size')
        self.assertContains(response, 'data-layout-capacity')
        self.assertContains(response, "10 x 15")
        self.assertContains(response, ">150</span>")
        self.assertContains(response, 'name="seat_cells"', count=150)
        self.assertContains(response, 'data-add-row="start"')
        self.assertContains(response, 'data-add-row="end"')
        self.assertContains(response, 'data-add-col="start"')
        self.assertContains(response, 'data-add-col="end"')
        self.assertContains(response, 'data-delete-row=', count=10)
        self.assertContains(response, 'data-delete-col=', count=15)
        self.assertNotContains(response, 'name="grid_rows"')
        self.assertNotContains(response, 'name="grid_cols"')
        self.assertNotContains(response, '<select name="studio_type"')

    def test_manager_studio_create_infers_saved_dimensions_from_grid(self):
        manager = make_role_user("studio_grid_manager", "manager")
        self.client.force_login(manager)

        response = self.client.post(
            reverse("cinema:manager_studio_new"),
            {
                "name": "Studio Grid",
                "studio_type": self.studio_type.id,
                "layout_rows": 2,
                "layout_cols": 3,
                "seat_cells": ["0,0", "1,2"],
            },
        )

        self.assertRedirects(response, reverse("cinema:manager_studios"))
        studio = Studio.objects.get(name="Studio Grid")
        self.assertEqual(studio.grid_rows, 2)
        self.assertEqual(studio.grid_cols, 3)
        self.assertEqual(studio.capacity, 2)
        self.assertTrue(Seat.objects.filter(studio=studio, grid_y_pos=1, grid_x_pos=2).exists())

    def test_manager_studio_list_rows_link_to_detail_without_status_controls(self):
        manager = make_role_user("studio_list_manager", "manager")
        self.client.force_login(manager)
        inactive = Studio.objects.create(
            name="Studio Arsip",
            studio_type=self.studio_type,
            grid_rows=1,
            grid_cols=1,
            is_active=False,
        )
        save_studio_layout(inactive, {(0, 0)})

        response = self.client.get(reverse("cinema:manager_studios"))

        self.assertContains(response, reverse("cinema:manager_studio_detail", args=[self.studio.id]))
        self.assertContains(response, "manager-studio-link")
        self.assertContains(response, reverse("cinema:manager_studios_inactive"))
        self.assertContains(response, "Studio Nonaktif")
        self.assertContains(response, "Tambah Studio")
        self.assertNotContains(response, inactive.name)
        self.assertNotContains(response, "<th>Grid</th>")
        self.assertNotContains(response, "<th>Status</th>")
        self.assertNotContains(response, ">Edit</a>")
        self.assertNotContains(response, 'class="toggle-switch-input"')
        self.assertNotContains(response, 'role="switch"')
        self.assertNotContains(response, "status-badge")

    def test_manager_inactive_studio_list_only_shows_inactive_and_links_back(self):
        manager = make_role_user("studio_inactive_list_manager", "manager")
        self.client.force_login(manager)
        inactive = Studio.objects.create(
            name="Studio Lama",
            studio_type=self.studio_type,
            grid_rows=1,
            grid_cols=1,
            is_active=False,
        )
        save_studio_layout(inactive, {(0, 0)})

        response = self.client.get(reverse("cinema:manager_studios_inactive"))

        self.assertContains(response, "Studio Nonaktif")
        self.assertContains(response, reverse("cinema:manager_studios"))
        self.assertContains(response, "Kembali")
        self.assertContains(response, inactive.name)
        self.assertContains(response, reverse("cinema:manager_studio_detail", args=[inactive.id]))
        self.assertNotContains(response, self.studio.name)
        self.assertNotContains(response, "Tambah Studio")
        self.assertNotContains(response, "<th>Grid</th>")
        self.assertNotContains(response, "<th>Status</th>")

    def test_manager_studio_detail_shell_loads_htmx_partial(self):
        manager = make_role_user("studio_detail_manager", "manager")
        self.client.force_login(manager)

        response = self.client.get(reverse("cinema:manager_studio_detail", args=[self.studio.id]))

        self.assertContains(response, 'id="manager-studio-detail"')
        self.assertContains(response, reverse("cinema:manager_studio_detail_partial", args=[self.studio.id]))
        self.assertContains(response, 'hx-trigger="load"')
        self.assertContains(response, 'hx-swap="outerHTML"')

    def test_manager_studio_detail_partial_switches_to_update_mode_with_readonly_seatmap(self):
        manager = make_role_user("studio_edit_manager", "manager")
        self.client.force_login(manager)
        studio = Studio.objects.create(name="Studio Readonly", studio_type=self.studio_type, grid_rows=2, grid_cols=3)
        save_studio_layout(studio, {(0, 0), (1, 2)})

        detail_response = self.client.get(reverse("cinema:manager_studio_detail_partial", args=[studio.id]))
        update_response = self.client.get(
            reverse("cinema:manager_studio_detail_partial", args=[studio.id]),
            {"mode": "update"},
        )

        self.assertContains(detail_response, "?mode=update")
        self.assertContains(detail_response, "Nonaktifkan")
        self.assertContains(detail_response, reverse("cinema:manager_studio_toggle", args=[studio.id]))
        self.assertContains(detail_response, "studio-layout-readonly")
        self.assertContains(detail_response, "studio-readonly-cell-seat")
        self.assertContains(detail_response, "studio-readonly-cell-empty")
        self.assertNotContains(detail_response, "studio-layout-note")
        self.assertNotContains(detail_response, "Anda tidak dapat mengubah / mengatur ulang seatmap")
        self.assertContains(update_response, reverse("cinema:manager_studio_edit", args=[studio.id]))
        self.assertContains(update_response, "Nonaktifkan")
        self.assertContains(update_response, reverse("cinema:manager_studio_toggle", args=[studio.id]))
        self.assertContains(update_response, 'hx-target="#manager-studio-detail"')
        self.assertContains(update_response, 'class="choice-pool"')
        self.assertContains(update_response, 'type="radio"')
        self.assertContains(update_response, f"{studio.grid_rows} x {studio.grid_cols}")
        self.assertContains(update_response, str(studio.capacity))
        self.assertContains(update_response, "Seatmap")
        self.assertContains(update_response, "studio-layout-readonly")
        self.assertContains(update_response, "studio-layout-note")
        self.assertContains(update_response, "Anda tidak dapat mengubah / mengatur ulang seatmap")
        self.assertContains(update_response, "A1")
        self.assertNotContains(update_response, "Kursi aktif")
        self.assertNotContains(update_response, "Tidak aktif")
        self.assertNotContains(update_response, "data-studio-layout")
        self.assertNotContains(update_response, "data-add-row")
        self.assertNotContains(update_response, "data-add-col")
        self.assertNotContains(update_response, "data-delete-row")
        self.assertNotContains(update_response, "data-delete-col")
        self.assertNotContains(update_response, 'name="layout_rows"')
        self.assertNotContains(update_response, 'name="layout_cols"')
        self.assertNotContains(update_response, 'name="seat_cells"')

    def test_manager_studio_edit_keeps_existing_seat_layout_immutable(self):
        manager = make_role_user("studio_immutable_manager", "manager")
        self.client.force_login(manager)
        studio = Studio.objects.create(name="Studio Immutable", studio_type=self.studio_type, grid_rows=2, grid_cols=3)
        save_studio_layout(studio, {(0, 0), (0, 2), (1, 1)})
        original_positions = set(studio.seats.values_list("grid_y_pos", "grid_x_pos"))
        original_seat_ids = set(studio.seats.values_list("id", flat=True))

        response = self.client.post(
            reverse("cinema:manager_studio_edit", args=[studio.id]),
            {
                "name": "Studio Renamed",
                "studio_type": self.studio_type.id,
                "layout_rows": 1,
                "layout_cols": 1,
                "seat_cells": ["0,0"],
            },
        )

        self.assertRedirects(response, reverse("cinema:manager_studio_detail", args=[studio.id]))
        studio.refresh_from_db()
        self.assertEqual(studio.name, "Studio Renamed")
        self.assertEqual(studio.grid_rows, 2)
        self.assertEqual(studio.grid_cols, 3)
        self.assertEqual(set(studio.seats.values_list("grid_y_pos", "grid_x_pos")), original_positions)
        self.assertEqual(set(studio.seats.values_list("id", flat=True)), original_seat_ids)

    def test_manager_studio_htmx_update_self_replaces_partial(self):
        manager = make_role_user("studio_htmx_manager", "manager")
        self.client.force_login(manager)

        response = self.client.post(
            reverse("cinema:manager_studio_edit", args=[self.studio.id]),
            {"name": "Studio HTMX", "studio_type": self.studio_type.id},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.studio.refresh_from_db()
        self.assertEqual(self.studio.name, "Studio HTMX")
        self.assertContains(response, 'id="manager-studio-detail"')
        self.assertContains(response, "Detail Studio")
        self.assertContains(response, "Studio HTMX")
        self.assertContains(response, "?mode=update")
        self.assertNotContains(response, "<!doctype html>")

    def test_manager_studio_htmx_disable_returns_detail_partial_inactive(self):
        manager = make_role_user("studio_disable_manager", "manager")
        self.client.force_login(manager)

        response = self.client.post(
            reverse("cinema:manager_studio_toggle", args=[self.studio.id]),
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.studio.refresh_from_db()
        self.assertFalse(self.studio.is_active)
        self.assertContains(response, 'id="manager-studio-detail"')
        self.assertContains(response, "Detail Studio")
        self.assertContains(response, "badge-inactive")
        self.assertNotContains(response, "?mode=update")
        self.assertNotContains(response, "Ubah Studio")
        self.assertNotContains(response, "Nonaktifkan")
        self.assertContains(response, "Pulihkan")
        self.assertContains(response, reverse("cinema:manager_studio_restore", args=[self.studio.id]))
        self.assertNotContains(response, "<!doctype html>")

    def test_manager_studio_inactive_update_mode_get_is_blocked(self):
        manager = make_role_user("studio_inactive_get_manager", "manager")
        self.client.force_login(manager)
        self.studio.is_active = False
        self.studio.save(update_fields=["is_active"])

        detail_response = self.client.get(reverse("cinema:manager_studio_detail_partial", args=[self.studio.id]))
        update_response = self.client.get(
            reverse("cinema:manager_studio_detail_partial", args=[self.studio.id]),
            {"mode": "update"},
            headers={"HX-Request": "true"},
        )

        self.assertFalse(self.studio.is_editable)
        self.assertNotContains(detail_response, "?mode=update")
        self.assertNotContains(detail_response, ">Edit<")
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.content, b"")
        self.assertEqual(update_response.headers["HX-Reswap"], "none")
        self.assertIn("Studio nonaktif tidak dapat diedit.", update_response.headers["HX-Trigger"])

    def test_manager_studio_inactive_update_post_is_blocked(self):
        manager = make_role_user("studio_inactive_post_manager", "manager")
        self.client.force_login(manager)
        self.studio.is_active = False
        self.studio.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("cinema:manager_studio_edit", args=[self.studio.id]),
            {"name": "Should Not Change", "studio_type": self.studio_type.id},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["HX-Reswap"], "none")
        self.assertIn("Studio nonaktif tidak dapat diedit.", response.headers["HX-Trigger"])
        self.studio.refresh_from_db()
        self.assertNotEqual(self.studio.name, "Should Not Change")
        self.assertFalse(self.studio.is_active)

    def test_manager_studio_inactive_deactivate_post_is_blocked(self):
        manager = make_role_user("studio_deactivate_block_manager", "manager")
        self.client.force_login(manager)
        self.studio.is_active = False
        self.studio.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("cinema:manager_studio_toggle", args=[self.studio.id]),
            headers={"HX-Request": "true"},
        )

        self.studio.refresh_from_db()
        self.assertFalse(self.studio.is_active)
        self.assertFalse(self.studio.is_deactivable)
        self.assertTrue(self.studio.is_restorable)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["HX-Reswap"], "none")
        self.assertIn("Studio nonaktif tidak perlu dinonaktifkan.", response.headers["HX-Trigger"])

    def test_manager_studio_htmx_restore_returns_detail_partial_active(self):
        manager = make_role_user("studio_restore_manager", "manager")
        self.client.force_login(manager)
        self.studio.is_active = False
        self.studio.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("cinema:manager_studio_restore", args=[self.studio.id]),
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.studio.refresh_from_db()
        self.assertTrue(self.studio.is_active)
        self.assertTrue(self.studio.is_editable)
        self.assertFalse(self.studio.is_restorable)
        self.assertContains(response, 'id="manager-studio-detail"')
        self.assertContains(response, "Detail Studio")
        self.assertContains(response, "badge-active")
        self.assertContains(response, "?mode=update")
        self.assertContains(response, "Nonaktifkan")
        self.assertNotContains(response, "Pulihkan")
        self.assertNotContains(response, "<!doctype html>")

    def test_manager_studio_active_restore_post_is_blocked(self):
        manager = make_role_user("studio_restore_block_manager", "manager")
        self.client.force_login(manager)

        response = self.client.post(
            reverse("cinema:manager_studio_restore", args=[self.studio.id]),
            headers={"HX-Request": "true"},
        )

        self.assertTrue(self.studio.is_active)
        self.assertFalse(self.studio.is_restorable)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["HX-Reswap"], "none")
        self.assertIn("Studio aktif tidak perlu dipulihkan.", response.headers["HX-Trigger"])

    def test_scheduler_create_view_marks_jadwalkan_navigation_active(self):
        scheduler = make_role_user("nav_scheduler", "scheduler")
        self.client.force_login(scheduler)

        response = self.client.get(reverse("cinema:scheduler_showtime_new"))

        active_items = [item["label"] for item in response.context["navigation_items"] if item["active"]]
        self.assertEqual(active_items, ["Jadwalkan"])
        self.assertEqual(
            [item["label"] for item in response.context["navigation_items"]],
            ["Daftar Showtime", "Jadwalkan", "Stub Gateway"],
        )

    def test_scheduler_showtime_create_uses_phased_visual_wizard(self):
        scheduler = make_role_user("wizard_scheduler", "scheduler")
        self.client.force_login(scheduler)
        self.movie.main_picture = "images/movies/main-pictures/ruang-sunyi.jpg"
        self.movie.save(update_fields=["main_picture"])

        response = self.client.get(reverse("cinema:scheduler_showtime_new"))

        self.assertContains(response, 'data-showtime-wizard')
        self.assertContains(response, 'data-confirm-mode="success"')
        self.assertContains(response, 'data-confirm-title="Jadwalkan jam tayang?"')
        self.assertContains(response, 'data-confirm-yes="Jadwalkan"')
        self.assertContains(response, 'id="scheduler-wizard-data"')
        self.assertContains(response, 'data-step-panel="1"')
        self.assertContains(response, 'data-step-panel="2"')
        self.assertContains(response, 'data-step-panel="3"')
        self.assertContains(response, 'data-past-time-message')
        self.assertContains(response, 'data-selected-movie-media')
        self.assertContains(response, 'class="scheduler-movie-card has-image"')
        self.assertContains(response, self.movie.main_picture.url)
        self.assertContains(response, self.movie.get_age_rating_display())
        self.assertContains(response, "Ruang Sunyi")
        self.assertContains(response, "Studio 1")
        self.assertContains(response, "scheduler-showtime.js")

    def test_scheduler_showtime_wizard_posts_to_existing_create_flow(self):
        scheduler = make_role_user("wizard_post_scheduler", "scheduler")
        self.client.force_login(scheduler)
        start_at = timezone.localtime(self.showtime.end_at + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            reverse("cinema:scheduler_showtime_new"),
            {
                "movie": self.movie.id,
                "studio": self.studio.id,
                "start_at": start_at,
                "price": 50000,
            },
        )

        self.assertRedirects(response, reverse("cinema:scheduler_showtimes"))
        self.assertTrue(ShowTime.objects.filter(movie=self.movie, studio=self.studio, price=50000).exists())

    def test_scheduler_showtime_create_rejects_past_start_at(self):
        scheduler = make_role_user("wizard_past_scheduler", "scheduler")
        self.client.force_login(scheduler)
        start_at = timezone.localtime(timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            reverse("cinema:scheduler_showtime_new"),
            {
                "movie": self.movie.id,
                "studio": self.studio.id,
                "start_at": start_at,
                "price": 50000,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jam mulai tidak boleh lebih awal dari waktu saat ini.")

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
