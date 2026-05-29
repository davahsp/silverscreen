from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import AgeRating, Movie, MovieTheme, Product, ProductCategory, ShowTime, Studio, StudioType
from .services.scheduling import PAST_START_MESSAGE, derive_showtime_fields, save_showtime, validate_showtime_window
from .widgets import ImageWidget


class CustomerSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class MovieForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["age_rating"].choices = AgeRating.choices

    class Meta:
        model = Movie
        fields = ["title", "synopsis", "age_rating", "main_picture", "runtime_minutes", "movie_theme", "is_active"]
        labels = {
            "title": "Judul",
            "synopsis": "Sinopsis",
            "age_rating": "Rating Umur",
            "main_picture": "Gambar Utama",
            "runtime_minutes": "Durasi Film (menit)",
            "movie_theme": "Tema Film",
            "is_active": "Status Film",
        }
        widgets = {
            "synopsis": forms.Textarea(attrs={"rows": 4}),
            "age_rating": forms.RadioSelect(attrs={"class": "choice-pool-input"}),
            "movie_theme": forms.RadioSelect(attrs={"class": "choice-pool-input"}),
            "main_picture": ImageWidget(),
        }

    def save(self, commit=True):
        old_main_picture = None
        if self.instance.pk:
            old_main_picture = (
                type(self.instance)
                .objects.filter(pk=self.instance.pk)
                .values_list("main_picture", flat=True)
                .first()
            )
        movie = super().save(commit=commit)
        clear_name = self.fields["main_picture"].widget.clear_checkbox_name("main_picture")
        if commit and old_main_picture and clear_name in self.data and not movie.main_picture:
            movie._meta.get_field("main_picture").storage.delete(old_main_picture)
        return movie


class MovieThemeForm(forms.ModelForm):
    class Meta:
        model = MovieTheme
        fields = ["name"]


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = ProductCategory.choices

    class Meta:
        model = Product
        fields = ["name", "price", "category", "picture", "is_active"]
        labels = {
            "name": "Nama Produk",
            "price": "Harga",
            "category": "Kategori",
            "picture": "Gambar Produk",
            "is_active": "Status Produk",
        }
        widgets = {
            "category": forms.RadioSelect(attrs={"class": "choice-pool-input"}),
            "picture": ImageWidget(),
        }

    def save(self, commit=True):
        old_picture = None
        if self.instance.pk:
            old_picture = (
                type(self.instance)
                .objects.filter(pk=self.instance.pk)
                .values_list("picture", flat=True)
                .first()
            )
        product = super().save(commit=commit)
        clear_name = self.fields["picture"].widget.clear_checkbox_name("picture")
        if commit and old_picture and clear_name in self.data and not product.picture:
            product._meta.get_field("picture").storage.delete(old_picture)
        return product


class StudioTypeForm(forms.ModelForm):
    class Meta:
        model = StudioType
        fields = ["name", "base_price", "picture"]


class StudioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["studio_type"].empty_label = None

    class Meta:
        model = Studio
        fields = ["name", "studio_type"]
        labels = {
            "name": "Nama Studio",
            "studio_type": "Tipe Studio",
        }
        widgets = {
            "studio_type": forms.RadioSelect(attrs={"class": "choice-pool-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            return cleaned
        try:
            rows = int(self.data.get("layout_rows", ""))
            cols = int(self.data.get("layout_cols", ""))
        except ValueError:
            rows = 0
            cols = 0
        self.instance.grid_rows = max(rows, 1)
        self.instance.grid_cols = max(cols, 1)
        return cleaned


class ShowTimeForm(forms.Form):
    movie = forms.ModelChoiceField(queryset=Movie.objects.filter(is_active=True))
    studio = forms.ModelChoiceField(queryset=Studio.objects.filter(is_active=True))
    start_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    price = forms.IntegerField(min_value=1)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance:
            self.fields["movie"].initial = instance.movie
            self.fields["studio"].initial = instance.studio
            self.fields["start_at"].initial = instance.start_at
            self.fields["price"].initial = instance.price

    def clean(self):
        cleaned = super().clean()
        movie = cleaned.get("movie")
        studio = cleaned.get("studio")
        start_at = cleaned.get("start_at")
        if movie and studio and start_at:
            if start_at < timezone.now():
                raise forms.ValidationError(PAST_START_MESSAGE)
            _duration, end_at = derive_showtime_fields(movie, start_at)
            try:
                validate_showtime_window(studio, start_at, end_at, current_id=self.instance.pk if self.instance else None)
            except forms.ValidationError as exc:
                raise exc
            cleaned["duration_minutes"] = movie.runtime_minutes
            cleaned["end_at"] = end_at
        return cleaned

    def save(self):
        return save_showtime(
            movie=self.cleaned_data["movie"],
            studio=self.cleaned_data["studio"],
            start_at=self.cleaned_data["start_at"],
            price=self.cleaned_data["price"],
            showtime=self.instance,
        )


class SeatSelectionForm(forms.Form):
    seats = forms.CharField(required=True)

    def clean_seats(self):
        raw = self.cleaned_data["seats"]
        try:
            seat_ids = [int(value) for value in raw.split(",") if value]
        except ValueError as exc:
            raise forms.ValidationError("Pilihan kursi tidak valid.") from exc
        if not seat_ids:
            raise forms.ValidationError("Pilih minimal satu kursi.")
        return seat_ids
