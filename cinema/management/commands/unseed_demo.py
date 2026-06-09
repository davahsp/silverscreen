from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from cinema.models import Movie, MovieTheme, Product, ShowTime, Studio, StudioType


DEMO_USERNAMES = ["customer", "staff", "scheduler", "manager"]
DEMO_GROUP_NAMES = ["customer", "staff", "scheduler", "manager"]
DEMO_THEME_NAMES = ["Drama", "Sci-Fi", "Horror", "Family", "Documentary"]
DEMO_STUDIO_TYPE_NAMES = ["Regular", "Premiere", "IMAX"]
DEMO_MOVIE_TITLES = [
    "Ruang Sunyi",
    "Galaksi Terakhir",
    "Rumah di Belakang Layar",
    "Petualangan Raka",
    "Arsip Film Lama",
]
DEMO_PRODUCT_NAMES = [
    "Popcorn Regular",
    "Popcorn Large",
    "Iced Tea",
    "Cola",
    "Couple Combo",
    "Movie Poster",
    "Legacy Snack",
]
DEMO_STUDIO_NAMES = ["Studio 1", "Studio 2", "Studio 3"]


class Command(BaseCommand):
    help = "Remove data created by the Silver Screen demo seeder."

    @transaction.atomic
    def handle(self, *args, **options):
        demo_showtimes = ShowTime.objects.filter(
            movie__title__in=DEMO_MOVIE_TITLES,
            studio__name__in=DEMO_STUDIO_NAMES,
        )
        deleted_showtimes, _ = demo_showtimes.delete()

        deleted_studios, _ = Studio.objects.filter(name__in=DEMO_STUDIO_NAMES).delete()
        deleted_movies, _ = Movie.objects.filter(title__in=DEMO_MOVIE_TITLES).delete()
        deleted_products, _ = Product.objects.filter(name__in=DEMO_PRODUCT_NAMES).delete()
        deleted_themes, _ = MovieTheme.objects.filter(name__in=DEMO_THEME_NAMES).delete()
        deleted_studio_types, _ = StudioType.objects.filter(name__in=DEMO_STUDIO_TYPE_NAMES).delete()
        deleted_users, _ = User.objects.filter(username__in=DEMO_USERNAMES).delete()

        empty_demo_groups = Group.objects.filter(name__in=DEMO_GROUP_NAMES, user__isnull=True)
        deleted_groups, _ = empty_demo_groups.delete()

        total = sum(
            [
                deleted_showtimes,
                deleted_studios,
                deleted_movies,
                deleted_products,
                deleted_themes,
                deleted_studio_types,
                deleted_users,
                deleted_groups,
            ]
        )
        self.stdout.write(self.style.SUCCESS(f"Demo data removed ({total} records deleted)."))
