from django.core.exceptions import ValidationError
from django.db import transaction

from cinema.models import Seat, Studio

ROW_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@transaction.atomic
def save_studio_layout(studio, active_positions):
    if not studio.name:
        raise ValidationError("Nama studio wajib diisi.")
    if not studio.studio_type_id:
        raise ValidationError("Tipe studio wajib diisi.")
    if studio.grid_rows < 1 or studio.grid_cols < 1:
        raise ValidationError("Ukuran grid tidak valid.")
    if not active_positions:
        raise ValidationError("Layout harus memiliki minimal satu kursi.")
    studio.save()
    studio.seats.all().delete()
    for y in range(studio.grid_rows):
        seat_count = 0
        for x in range(studio.grid_cols):
            if (y, x) not in active_positions:
                continue
            seat_count += 1
            row = ROW_LABELS[y]
            Seat.objects.create(
                studio=studio,
                number=f"{row}{seat_count}",
                row=row,
                grid_x_pos=x,
                grid_y_pos=y,
                is_active=True,
            )
    return Studio.objects.get(pk=studio.pk)
