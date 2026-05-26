import json
from datetime import timedelta

from django.core.exceptions import ValidationError
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
    OrderSource,
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
from cinema.services.cancellation import PRINTED_CANCEL_MESSAGE, cancel_order
from cinema.services.payments import apply_payment_callback
from cinema.services.scheduling import disable_showtime, save_showtime
from cinema.services.studios import save_studio_layout


class SilverScreenServiceTests(TestCase):
    def setUp(self):
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

        self.assertEqual(order.source, OrderSource.ONLINE)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.tickets.get().status, TicketStatus.HELD)
        self.assertEqual(order.payment.status, PaymentStatus.UNPAID)
        self.assertTrue(order.payment.gateway_payment_id)
        self.assertTrue(order.payment.payment_url)

    def test_online_order_prevents_unavailable_seats(self):
        create_online_order(self.showtime.id, [self.seats[0].id], [])

        with self.assertRaises(ValidationError):
            create_online_order(self.showtime.id, [self.seats[0].id], [])

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
        self.assertEqual(order.tickets.get().status, TicketStatus.CONFIRMED)

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

    def test_unpaid_cancellation_sets_canceled_before_paid(self):
        order = create_online_order(self.showtime.id, [self.seats[0].id], [])

        cancel_order(order.number)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELED)
        self.assertEqual(order.payment.status, PaymentStatus.CANCELED_BEFORE_PAID)
        self.assertEqual(order.tickets.get().status, TicketStatus.CANCELED)

    def test_paid_unprinted_cancellation_goes_to_refund_queue(self):
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

    def test_printed_ticket_cancellation_is_blocked(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [])

        with self.assertRaisesMessage(ValidationError, PRINTED_CANCEL_MESSAGE):
            cancel_order(order.number)

    def test_onsite_order_is_confirmed_paid_and_printed_without_pending(self):
        order = create_onsite_order(self.showtime.id, [self.seats[0].id], [(self.product.id, 1)])

        self.assertEqual(order.source, OrderSource.ONSITE)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(order.payment.status, PaymentStatus.PAID)
        ticket = order.tickets.get()
        self.assertEqual(ticket.status, TicketStatus.PRINTED)
        self.assertIsNotNone(ticket.printed_at)

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

    def test_studio_capacity_and_zero_seat_validation(self):
        self.assertEqual(self.studio.capacity, 3)
        empty = Studio(name="Studio Empty", studio_type=self.studio_type, grid_rows=1, grid_cols=1)
        with self.assertRaises(ValidationError):
            save_studio_layout(empty, set())

    def test_inactive_movies_and_products_hidden_from_customer_pages(self):
        response = self.client.get(reverse("cinema:movies"))
        self.assertContains(response, self.movie.title)
        self.assertNotContains(response, self.inactive_movie.title)

        response = self.client.post(reverse("cinema:booking", args=[self.showtime.id]), {"quantity": 1})
        self.assertRedirects(response, reverse("cinema:booking_seats", args=[self.showtime.id]))
        response = self.client.post(reverse("cinema:booking_seats", args=[self.showtime.id]), {"seats": [self.seats[0].id]})
        self.assertRedirects(response, reverse("cinema:booking_addons", args=[self.showtime.id]))
        response = self.client.get(reverse("cinema:booking_addons", args=[self.showtime.id]))
        self.assertContains(response, "Jumlah Tiket")
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
        response = self.client.post(reverse("cinema:booking", args=[self.showtime.id]), {"quantity": 0})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "django-messages-data")
        self.assertContains(response, "Jumlah tiket harus 1 sampai 10.")

    def test_htmx_messages_are_sent_in_trigger_header(self):
        response = self.client.post(
            reverse("cinema:booking", args=[self.showtime.id]),
            {"quantity": 0},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        trigger = json.loads(response.headers["HX-Trigger"])
        self.assertEqual(trigger["ss:messages"]["messages"][0]["message"], "Jumlah tiket harus 1 sampai 10.")
        self.assertIn("error", trigger["ss:messages"]["messages"][0]["tags"])

    def test_htmx_messages_are_consumed_after_trigger_header(self):
        message_text = "Jumlah tiket harus 1 sampai 10."
        self.client.post(
            reverse("cinema:booking", args=[self.showtime.id]),
            {"quantity": 0},
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
