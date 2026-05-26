from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AgeRating, Movie, MovieTheme, Product, ProductCategory, ShowTime, Studio, StudioType
from .services.scheduling import derive_showtime_fields, save_showtime, validate_showtime_window


class CustomerSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ["title", "synopsis", "age_rating", "main_picture", "runtime_minutes", "movie_theme", "is_active"]
        widgets = {
            "synopsis": forms.Textarea(attrs={"rows": 4}),
            "age_rating": forms.Select(choices=AgeRating.choices),
        }


class MovieThemeForm(forms.ModelForm):
    class Meta:
        model = MovieTheme
        fields = ["name"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "price", "category", "is_active"]
        widgets = {"category": forms.Select(choices=ProductCategory.choices)}


class StudioTypeForm(forms.ModelForm):
    class Meta:
        model = StudioType
        fields = ["name", "base_price", "picture"]


class StudioForm(forms.ModelForm):
    class Meta:
        model = Studio
        fields = ["name", "studio_type", "grid_rows", "grid_cols", "is_active"]


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
