from django.core.management.base import BaseCommand
from django.db import transaction

from cinema.management.commands._seed_data import MOVIES, MOVIE_THEMES, PRODUCTS, STUDIOS, STUDIO_TYPES
from cinema.models import Movie, MovieTheme, Product, Studio, StudioType
from cinema.services.studios import save_studio_layout


def expected_active_positions(rows, cols, aisles):
    return {(y, x) for y in range(rows) for x in range(cols) if (y, x) not in aisles}


def studio_layout_matches(studio, active_positions):
    seats = studio.seats.all()
    if seats.count() != len(active_positions):
        return False
    return set(seats.filter(is_active=True).values_list("grid_y_pos", "grid_x_pos")) == active_positions


class Command(BaseCommand):
    help = "Seed active movie, cinema, and product master data."

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        themes = {}
        for name in MOVIE_THEMES:
            theme, created = MovieTheme.objects.get_or_create(name=name)
            themes[name] = theme
            created_count += created
            updated_count += not created

        studio_types = {}
        for name, base_price in STUDIO_TYPES:
            studio_type, created = StudioType.objects.update_or_create(
                name=name,
                defaults={"base_price": base_price},
            )
            studio_types[name] = studio_type
            created_count += created
            updated_count += not created

        for title, synopsis, rating, runtime, theme_name in MOVIES:
            _movie, created = Movie.objects.update_or_create(
                title=title,
                defaults={
                    "synopsis": synopsis,
                    "age_rating": rating,
                    "runtime_minutes": runtime,
                    "movie_theme": themes[theme_name],
                    "is_active": True,
                },
            )
            created_count += created
            updated_count += not created

        for name, category, price in PRODUCTS:
            _product, created = Product.objects.update_or_create(
                name=name,
                defaults={"category": category, "price": price, "is_active": True},
            )
            created_count += created
            updated_count += not created

        rebuilt_layouts = 0
        for name, studio_type_name, rows, cols, aisles in STUDIOS:
            studio, _created = Studio.objects.get_or_create(
                name=name,
                defaults={
                    "studio_type": studio_types[studio_type_name],
                    "grid_rows": rows,
                    "grid_cols": cols,
                    "is_active": True,
                },
            )
            created_count += _created
            updated_count += not _created
            active_positions = expected_active_positions(rows, cols, aisles)
            dimensions_changed = studio.grid_rows != rows or studio.grid_cols != cols
            studio.studio_type = studio_types[studio_type_name]
            studio.grid_rows = rows
            studio.grid_cols = cols
            studio.is_active = True

            if dimensions_changed or not studio_layout_matches(studio, active_positions):
                save_studio_layout(studio, active_positions)
                rebuilt_layouts += 1
            else:
                studio.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Master data seeded ({len(MOVIES)} movies, {len(STUDIOS)} studios, "
                f"{len(PRODUCTS)} products; {created_count} records created, "
                f"{updated_count} records updated, {rebuilt_layouts} layouts rebuilt)."
            )
        )
