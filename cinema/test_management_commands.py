from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from cinema.models import Movie, MovieTheme, Product, ShowTime, Studio, StudioType
from cinema.management.commands.unseed_demo import (
    DEMO_GROUP_NAMES,
    DEMO_MOVIE_TITLES,
    DEMO_PRODUCT_NAMES,
    DEMO_STUDIO_NAMES,
    DEMO_STUDIO_TYPE_NAMES,
    DEMO_THEME_NAMES,
    DEMO_USERNAMES,
)


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
