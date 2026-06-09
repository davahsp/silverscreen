from datetime import datetime, time, timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cinema.management.commands._seed_data import (
    AUTH_USERS,
    MOVIES,
    SHOWTIME_DAYS,
    SHOWTIME_HOURS,
    STUDIOS,
)
from cinema.models import Movie, ShowTime, Studio
from cinema.services.scheduling import save_showtime


class Command(BaseCommand):
    help = "Seed showtimes from D+1 through D+14."

    def validate_dependencies(self):
        missing_auth = []
        for username, _password, role in AUTH_USERS:
            if not Group.objects.filter(name=role).exists():
                missing_auth.append(f"group {role}")
            if not User.objects.filter(username=username, groups__name=role).exists():
                missing_auth.append(f"user {username}")
        if missing_auth:
            raise CommandError(
                f"Missing authentication seed data: {', '.join(missing_auth)}. Run seed_auth first."
            )

        movie_titles = [movie[0] for movie in MOVIES]
        studio_names = [studio[0] for studio in STUDIOS]
        missing_movies = set(movie_titles) - set(
            Movie.objects.filter(title__in=movie_titles, is_active=True).values_list("title", flat=True)
        )
        missing_studios = set(studio_names) - set(
            Studio.objects.filter(name__in=studio_names, is_active=True).values_list("name", flat=True)
        )
        if missing_movies or missing_studios:
            missing = sorted(missing_movies | missing_studios)
            raise CommandError(f"Missing active master data: {', '.join(missing)}. Run seed_master_data first.")

    @transaction.atomic
    def handle(self, *args, **options):
        self.validate_dependencies()

        movies = list(Movie.objects.filter(title__in=[movie[0] for movie in MOVIES]))
        movies_by_title = {movie.title: movie for movie in movies}
        ordered_movies = [movies_by_title[movie[0]] for movie in MOVIES]
        studios = {
            studio.name: studio
            for studio in Studio.objects.select_related("studio_type").filter(name__in=[studio[0] for studio in STUDIOS])
        }
        first_date = timezone.localdate() + timedelta(days=1)
        created_count = 0
        updated_count = 0

        for day_index in range(SHOWTIME_DAYS):
            show_date = first_date + timedelta(days=day_index)
            for studio_index, (studio_name, _type, _rows, _cols, _aisles) in enumerate(STUDIOS):
                studio = studios[studio_name]
                for slot_index, hour in enumerate(SHOWTIME_HOURS):
                    start_at = timezone.make_aware(datetime.combine(show_date, time(hour=hour)))
                    movie_index = (
                        show_date.toordinal() * len(STUDIOS) * len(SHOWTIME_HOURS)
                        + studio_index * len(SHOWTIME_HOURS)
                        + slot_index
                    ) % len(ordered_movies)
                    showtime = ShowTime.objects.filter(studio=studio, start_at=start_at).first()
                    created = showtime is None
                    try:
                        save_showtime(
                            movie=ordered_movies[movie_index],
                            studio=studio,
                            start_at=start_at,
                            price=studio.studio_type.base_price,
                            showtime=showtime,
                        )
                    except ValidationError as exc:
                        raise CommandError(
                            f"Could not seed {studio.name} at {start_at:%Y-%m-%d %H:%M}: {'; '.join(exc.messages)}"
                        ) from exc
                    created_count += created
                    updated_count += not created

        self.stdout.write(
            self.style.SUCCESS(
                f"Showtimes seeded ({created_count} created, {updated_count} updated, "
                f"{SHOWTIME_DAYS} days scheduled)."
            )
        )
