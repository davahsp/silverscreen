from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from cinema.models import AgeRating, Movie, MovieTheme, Product, ProductCategory, ShowTime, Studio, StudioType
from cinema.services.scheduling import save_showtime
from cinema.services.studios import save_studio_layout


DEMO_USERS = [
    ("customer", "customer123", "customer"),
    ("staff", "staff123", "staff"),
    ("scheduler", "scheduler123", "scheduler"),
    ("manager", "manager123", "manager"),
]


class Command(BaseCommand):
    help = "Seed demo data for Silver Screen MVP."

    def handle(self, *args, **options):
        groups = {
            name: Group.objects.get_or_create(name=name)[0]
            for name in ["customer", "staff", "scheduler", "manager"]
        }
        for username, password, role in DEMO_USERS:
            user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@silverscreen.local"})
            if created:
                user.set_password(password)
                user.save()
            user.groups.add(groups[role])


        themes = {
            name: MovieTheme.objects.get_or_create(name=name)[0]
            for name in ["Drama", "Sci-Fi", "Horror", "Family", "Documentary"]
        }
        regular = StudioType.objects.get_or_create(name="Regular", defaults={"base_price": 45000})[0]
        premiere = StudioType.objects.get_or_create(name="Premiere", defaults={"base_price": 85000})[0]
        imax = StudioType.objects.get_or_create(name="IMAX", defaults={"base_price": 120000})[0]

        movies = [
            ("Ruang Sunyi", "Seorang pianis muda menemukan kembali makna dalam musik bersama seorang guru misterius.", AgeRating.R13, 112, themes["Drama"], True),
            ("Galaksi Terakhir", "Ekspedisi luar angkasa terakhir umat manusia menuju galaksi yang jauh.", AgeRating.R13, 128, themes["Sci-Fi"], True),
            ("Rumah di Belakang Layar", "Sebuah keluarga menemukan rahasia gelap di rumah tua pinggiran kota.", AgeRating.R17, 101, themes["Horror"], True),
            ("Petualangan Raka", "Raka dan sahabatnya mencari harta karun legendaris.", AgeRating.ALL_AGE, 95, themes["Family"], True),
            ("Arsip Film Lama", "Dokumenter sejarah industri film Indonesia dari koleksi arsip langka.", AgeRating.R7, 90, themes["Documentary"], False),
        ]
        movie_objs = []
        for title, synopsis, rating, runtime, theme, active in movies:
            movie, _created = Movie.objects.update_or_create(
                title=title,
                defaults={
                    "synopsis": synopsis,
                    "age_rating": rating,
                    "runtime_minutes": runtime,
                    "movie_theme": theme,
                    "is_active": active,
                },
            )
            movie_objs.append(movie)

        products = [
            ("Popcorn Regular", ProductCategory.FOOD, 30000, True),
            ("Popcorn Large", ProductCategory.FOOD, 45000, True),
            ("Iced Tea", ProductCategory.DRINK, 20000, True),
            ("Cola", ProductCategory.DRINK, 22000, True),
            ("Couple Combo", ProductCategory.COMBO, 75000, True),
            ("Movie Poster", ProductCategory.MERCHANDISE, 50000, True),
            ("Legacy Snack", ProductCategory.FOOD, 15000, False),
        ]
        for name, category, price, active in products:
            Product.objects.update_or_create(
                name=name,
                defaults={"category": category, "price": price, "is_active": active},
            )

        studio_specs = [
            ("Studio 1", regular, 8, 10, {(3, 4), (3, 5)}),
            ("Studio 2", premiere, 6, 8, {(2, 3), (2, 4)}),
            ("Studio 3", imax, 10, 12, {(4, 5), (4, 6), (5, 5), (5, 6)}),
        ]
        studios = []
        for name, studio_type, rows, cols, aisles in studio_specs:
            studio, _created = Studio.objects.get_or_create(
                name=name,
                defaults={"studio_type": studio_type, "grid_rows": rows, "grid_cols": cols},
            )
            studio.studio_type = studio_type
            studio.grid_rows = rows
            studio.grid_cols = cols
            studio.is_active = True
            active_positions = {(y, x) for y in range(rows) for x in range(cols) if (y, x) not in aisles}
            save_studio_layout(studio, active_positions)
            studios.append(studio)

        if not ShowTime.objects.exists():
            base = timezone.now().replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1)
            specs = [
                (movie_objs[0], studios[0], base + timedelta(hours=2), 45000),
                (movie_objs[0], studios[1], base + timedelta(hours=5), 85000),
                (movie_objs[1], studios[2], base + timedelta(hours=3), 120000),
                (movie_objs[2], studios[0], base + timedelta(hours=8), 50000),
                (movie_objs[3], studios[1], base, 90000),
            ]
            for movie, studio, start_at, price in specs:
                save_showtime(movie=movie, studio=studio, start_at=start_at, price=price)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
