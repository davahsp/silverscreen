from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from cinema.management.commands._seed_data import AUTH_USERS, MOVIES, PRODUCTS, SHOWTIME_DAYS, STUDIOS
from cinema.management.commands.unseed_demo import (
    DEMO_GROUP_NAMES,
    DEMO_MOVIE_TITLES,
    DEMO_PRODUCT_NAMES,
    DEMO_STUDIO_NAMES,
    DEMO_STUDIO_TYPE_NAMES,
    DEMO_THEME_NAMES,
    DEMO_USERNAMES,
)
from cinema.models import Movie, MovieTheme, Product, ShowTime, Studio, StudioType
from cinema.services.scheduling import save_showtime


class SeedAuthCommandTests(TestCase):
    def test_seeds_expected_groups_users_and_credentials_idempotently(self):
        unrelated_group = Group.objects.create(name="unrelated")

        call_command("seed_auth", stdout=StringIO())
        call_command("seed_auth", stdout=StringIO())

        self.assertEqual(Group.objects.filter(name__in=[user[2] for user in AUTH_USERS]).count(), 4)
        self.assertEqual(User.objects.filter(username__in=[user[0] for user in AUTH_USERS]).count(), 4)
        for username, password, role in AUTH_USERS:
            user = User.objects.get(username=username)
            self.assertEqual(user.email, f"{username}@silverscreen.local")
            self.assertTrue(user.check_password(password))
            self.assertTrue(user.groups.filter(name=role).exists())
        self.assertTrue(Group.objects.filter(pk=unrelated_group.pk).exists())


class SeedMasterDataCommandTests(TestCase):
    def test_seeds_active_master_data_and_preserves_matching_layouts(self):
        call_command("seed_master_data", stdout=StringIO())
        studio = Studio.objects.get(name="Studio 1")
        original_seat_ids = list(studio.seats.values_list("id", flat=True))
        Movie.objects.filter(title="Frozen 2").update(is_active=False)
        Product.objects.filter(name="Legacy Snack").update(is_active=False)
        Studio.objects.filter(name="Studio 1").update(is_active=False)

        output = StringIO()
        call_command("seed_master_data", stdout=output)

        self.assertEqual(Movie.objects.filter(title__in=[movie[0] for movie in MOVIES]).count(), len(MOVIES))
        self.assertEqual(Product.objects.filter(name__in=[product[0] for product in PRODUCTS]).count(), len(PRODUCTS))
        self.assertEqual(Studio.objects.filter(name__in=[studio[0] for studio in STUDIOS]).count(), len(STUDIOS))
        self.assertFalse(Movie.objects.filter(title__in=[movie[0] for movie in MOVIES], is_active=False).exists())
        self.assertFalse(Product.objects.filter(name__in=[product[0] for product in PRODUCTS], is_active=False).exists())
        self.assertFalse(Studio.objects.filter(name__in=[studio[0] for studio in STUDIOS], is_active=False).exists())
        self.assertEqual(list(studio.seats.values_list("id", flat=True)), original_seat_ids)
        self.assertIn("0 layouts rebuilt", output.getvalue())


class SeedShowtimeCommandTests(TestCase):
    def test_requires_auth_and_master_data(self):
        with self.assertRaisesMessage(CommandError, "Run seed_auth first"):
            call_command("seed_showtime", stdout=StringIO())

        call_command("seed_auth", stdout=StringIO())

        with self.assertRaisesMessage(CommandError, "Run seed_master_data first"):
            call_command("seed_showtime", stdout=StringIO())

    def test_seeds_fourteen_day_schedule_idempotently(self):
        call_command("seed_auth", stdout=StringIO())
        call_command("seed_master_data", stdout=StringIO())
        first_date = timezone.localdate() + timedelta(days=1)

        call_command("seed_showtime", stdout=StringIO())
        output = StringIO()
        call_command("seed_showtime", stdout=output)

        expected_count = SHOWTIME_DAYS * len(STUDIOS) * 3
        self.assertEqual(ShowTime.objects.count(), expected_count)
        self.assertFalse(ShowTime.objects.filter(is_active=False).exists())
        self.assertEqual(timezone.localtime(ShowTime.objects.earliest("start_at").start_at).date(), first_date)
        self.assertEqual(
            timezone.localtime(ShowTime.objects.latest("start_at").start_at).date(),
            first_date + timedelta(days=SHOWTIME_DAYS - 1),
        )
        for studio in Studio.objects.filter(name__in=[studio[0] for studio in STUDIOS]):
            self.assertEqual(ShowTime.objects.filter(studio=studio).count(), SHOWTIME_DAYS * 3)
            self.assertFalse(ShowTime.objects.filter(studio=studio).exclude(price=studio.studio_type.base_price).exists())
        self.assertIn(f"0 created, {expected_count} updated", output.getvalue())

        preserved = {
            (showtime.studio_id, showtime.start_at): showtime.movie_id
            for showtime in ShowTime.objects.filter(start_at__date=first_date + timedelta(days=1))
        }
        with patch("cinema.management.commands.seed_showtime.timezone.localdate", return_value=first_date):
            call_command("seed_showtime", stdout=StringIO())

        self.assertEqual(ShowTime.objects.count(), expected_count + len(STUDIOS) * 3)
        for showtime in ShowTime.objects.filter(start_at__date=first_date + timedelta(days=1)):
            self.assertEqual(showtime.movie_id, preserved[(showtime.studio_id, showtime.start_at)])

    def test_rolls_back_when_a_planned_slot_conflicts(self):
        call_command("seed_auth", stdout=StringIO())
        call_command("seed_master_data", stdout=StringIO())
        studio = Studio.objects.get(name="Studio 1")
        movie = Movie.objects.get(title="Gohan")
        start_at = timezone.localtime().replace(hour=10, minute=30, second=0, microsecond=0) + timedelta(days=1)
        save_showtime(movie=movie, studio=studio, start_at=start_at, price=studio.studio_type.base_price)

        with self.assertRaisesMessage(CommandError, "Could not seed Studio 1"):
            call_command("seed_showtime", stdout=StringIO())

        self.assertEqual(ShowTime.objects.count(), 1)


class UnseedDemoCommandTests(TestCase):
    def test_removes_demo_data_and_preserves_unrelated_group(self):
        unrelated_group = Group.objects.create(name="unrelated")
        call_command("legacy_seed_demo", stdout=StringIO())

        output = StringIO()
        call_command("unseed_demo", stdout=output)

        self.assertFalse(User.objects.filter(username__in=DEMO_USERNAMES).exists())
        self.assertFalse(Group.objects.filter(name__in=DEMO_GROUP_NAMES).exists())
        self.assertFalse(MovieTheme.objects.filter(name__in=DEMO_THEME_NAMES).exists())
        self.assertFalse(StudioType.objects.filter(name__in=DEMO_STUDIO_TYPE_NAMES).exists())
        self.assertFalse(Movie.objects.filter(title__in=DEMO_MOVIE_TITLES).exists())
        self.assertFalse(Product.objects.filter(name__in=DEMO_PRODUCT_NAMES).exists())
        self.assertFalse(Studio.objects.filter(name__in=DEMO_STUDIO_NAMES).exists())
        self.assertFalse(ShowTime.objects.exists())
        self.assertTrue(Group.objects.filter(pk=unrelated_group.pk).exists())
        self.assertIn("Demo data removed", output.getvalue())
