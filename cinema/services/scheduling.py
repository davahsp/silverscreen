from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from cinema.models import ShowTime, TicketStatus

ACTIVE_SHOWTIME_TICKET_STATUSES = [TicketStatus.HELD, TicketStatus.CONFIRMED, TicketStatus.PRINTED]
DISABLE_BLOCK_MESSAGE = "Showtime tidak dapat dinonaktifkan karena sudah memiliki tiket aktif."


def derive_showtime_fields(movie, start_at):
    duration_minutes = movie.runtime_minutes
    end_at = start_at + timedelta(minutes=duration_minutes)
    return duration_minutes, end_at


def validate_showtime_window(studio, start_at, end_at, current_id=None):
    overlaps = ShowTime.objects.filter(
        studio=studio,
        is_active=True,
        start_at__lt=end_at,
        end_at__gt=start_at,
    )
    if current_id:
        overlaps = overlaps.exclude(pk=current_id)
    if overlaps.exists():
        raise ValidationError("Studio sudah memiliki showtime aktif pada rentang waktu ini.")


@transaction.atomic
def save_showtime(*, movie, studio, start_at, price, showtime=None):
    if price < 1:
        raise ValidationError("Harga harus lebih dari 0.")
    duration_minutes, end_at = derive_showtime_fields(movie, start_at)
    validate_showtime_window(studio, start_at, end_at, current_id=showtime.pk if showtime else None)
    if showtime is None:
        showtime = ShowTime()
    showtime.movie = movie
    showtime.studio = studio
    showtime.start_at = start_at
    showtime.duration_minutes = duration_minutes
    showtime.end_at = end_at
    showtime.price = price
    showtime.is_active = True
    showtime.save()
    return showtime


@transaction.atomic
def disable_showtime(showtime_id):
    showtime = ShowTime.objects.select_for_update().get(id=showtime_id)
    if showtime.tickets.filter(status__in=ACTIVE_SHOWTIME_TICKET_STATUSES).exists():
        raise ValidationError(DISABLE_BLOCK_MESSAGE)
    showtime.is_active = False
    showtime.save(update_fields=["is_active"])
    return showtime
