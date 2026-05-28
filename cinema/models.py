from pathlib import Path

from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from django.utils import timezone


MOVIE_MAIN_PICTURE_DIR = "images/movies/main-pictures"


@deconstructible
class OverwriteMovieImageStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name


movie_main_picture_storage = OverwriteMovieImageStorage()


def movie_main_picture_upload_to(instance, filename):
    extension = Path(filename).suffix.lower() or ".jpg"
    if instance.pk:
        try:
            _dirs, files = movie_main_picture_storage.listdir(MOVIE_MAIN_PICTURE_DIR)
        except FileNotFoundError:
            files = []
        for existing in files:
            if Path(existing).stem == str(instance.pk):
                movie_main_picture_storage.delete(f"{MOVIE_MAIN_PICTURE_DIR}/{existing}")
        return f"{MOVIE_MAIN_PICTURE_DIR}/{instance.pk}{extension}"
    return f"{MOVIE_MAIN_PICTURE_DIR}/pending{extension}"


class AgeRating(models.TextChoices):
    ALL_AGE = "ALL_AGE", "Semua Usia"
    R7 = "R7", "R7+"
    R13 = "R13", "R13+"
    R17 = "R17", "R17+"
    R21 = "R21", "R21+"


class ProductCategory(models.TextChoices):
    FOOD = "FOOD", "Food"
    DRINK = "DRINK", "Drink"
    COMBO = "COMBO", "Combo"
    MERCHANDISE = "MERCHANDISE", "Merchandise"
    OTHER = "OTHER", "Other"


class OrderChannel(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    ONSITE = "ONSITE", "Onsite"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    EXPIRED = "EXPIRED", "Expired"
    CANCELED = "CANCELED", "Canceled"


class TicketStatus(models.TextChoices):
    HELD = "HELD", "Held"
    CONFIRMED = "CONFIRMED", "Confirmed"
    USED = "USED", "Used"
    EXPIRED = "EXPIRED", "Expired"
    CANCELED = "CANCELED", "Canceled"


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PAID = "PAID", "Paid"
    EXPIRED = "EXPIRED", "Expired"
    REFUND_PENDING = "REFUND_PENDING", "Refund Pending"
    REFUNDED = "REFUNDED", "Refunded"
    CANCELED_BEFORE_PAID = "CANCELED_BEFORE_PAID", "Canceled Before Paid"


class MovieTheme(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=180)
    synopsis = models.TextField()
    age_rating = models.CharField(max_length=20, choices=AgeRating.choices)
    main_picture = models.ImageField(
        upload_to=movie_main_picture_upload_to,
        storage=movie_main_picture_storage,
        blank=True,
    )
    runtime_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    movie_theme = models.ForeignKey(MovieTheme, on_delete=models.PROTECT)

    class Meta:
        ordering = ["title"]

    def clean(self):
        if self.runtime_minutes < 1:
            raise ValidationError({"runtime_minutes": "Durasi film harus lebih dari 0 menit."})

    def __str__(self):
        return self.title


class StudioType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    base_price = models.PositiveIntegerField()
    picture = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Studio(models.Model):
    name = models.CharField(max_length=80, unique=True)
    studio_type = models.ForeignKey(StudioType, on_delete=models.PROTECT)
    grid_rows = models.PositiveIntegerField()
    grid_cols = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    @property
    def capacity(self):
        if not self.pk:
            return 0
        return self.seats.filter(is_active=True).count()

    def clean(self):
        errors = {}
        if self.grid_rows < 1:
            errors["grid_rows"] = "Jumlah baris harus lebih dari 0."
        if self.grid_cols < 1:
            errors["grid_cols"] = "Jumlah kolom harus lebih dari 0."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class Seat(models.Model):
    studio = models.ForeignKey(Studio, related_name="seats", on_delete=models.CASCADE)
    number = models.CharField(max_length=12)
    row = models.CharField(max_length=4)
    grid_x_pos = models.PositiveIntegerField()
    grid_y_pos = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["studio", "grid_y_pos", "grid_x_pos"]
        constraints = [
            models.UniqueConstraint(fields=["studio", "number"], name="unique_seat_number_per_studio"),
            models.UniqueConstraint(fields=["studio", "grid_x_pos", "grid_y_pos"], name="unique_seat_position_per_studio"),
        ]

    def clean(self):
        if self.studio_id:
            if self.grid_x_pos >= self.studio.grid_cols or self.grid_y_pos >= self.studio.grid_rows:
                raise ValidationError("Posisi kursi berada di luar grid studio.")

    def __str__(self):
        return f"{self.studio} {self.number}"


class ShowTime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT)
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT)
    start_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    end_at = models.DateTimeField()
    price = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [models.Index(fields=["studio", "start_at", "end_at"])]

    def __str__(self):
        return f"{self.movie} - {self.studio} - {self.start_at:%Y-%m-%d %H:%M}"


class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=ProductCategory.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Order(models.Model):
    MAX_TICKETS = 10

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    number = models.CharField(max_length=32, unique=True)
    channel = models.CharField(max_length=10, choices=OrderChannel.choices)
    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    total_amount = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class Ticket(models.Model):
    code = models.CharField(max_length=32, unique=True)
    qr_identifier = models.UUIDField(null=True, blank=True, unique=True)
    order = models.ForeignKey(Order, related_name="tickets", on_delete=models.CASCADE)
    showtime = models.ForeignKey(ShowTime, related_name="tickets", on_delete=models.PROTECT)
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=TicketStatus.choices)

    class Meta:
        ordering = ["showtime", "seat__grid_y_pos", "seat__grid_x_pos"]
        constraints = [
            models.UniqueConstraint(
                fields=["showtime", "seat"],
                condition=Q(status__in=[TicketStatus.HELD, TicketStatus.CONFIRMED, TicketStatus.USED]),
                name="unique_active_ticket_per_showtime_seat",
            )
        ]

    def __str__(self):
        return self.code


class Payment(models.Model):
    internal_payment_id = models.CharField(max_length=32, unique=True)
    gateway_payment_id = models.CharField(max_length=32, blank=True)
    va_account = models.CharField(max_length=32, blank=True)
    order = models.OneToOneField(Order, related_name="payment", on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=PaymentStatus.choices)
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    payment_url = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return self.internal_payment_id


class OrderAddon(models.Model):
    order = models.ForeignKey(Order, related_name="addons", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()


class OrderCharge(models.Model):
    order = models.ForeignKey(Order, related_name="charges", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
