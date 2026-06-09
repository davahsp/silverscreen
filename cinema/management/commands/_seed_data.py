from cinema.models import AgeRating, ProductCategory


AUTH_USERS = [
    ("customer", "customer123", "customer"),
    ("staff", "staff123", "staff"),
    ("scheduler", "scheduler123", "scheduler"),
    ("manager", "manager123", "manager"),
]

MOVIE_THEMES = ["Drama", "Sci-Fi", "Horror", "Family", "Documentary"]

MOVIES = [
    (
        "Gohan",
        "Seekor anjing setia bernama Gohan menjalani petualangan yang mempererat hubungannya dengan keluarga tercinta.",
        AgeRating.R13,
        110,
        "Drama",
    ),
    (
        "Sore: Istri Dari Masa Depan",
        "Seorang perempuan dari masa depan hadir untuk mengubah kehidupan calon suaminya.",
        AgeRating.R13,
        120,
        "Drama",
    ),
    (
        "Interstellar",
        "Sekelompok penjelajah melintasi ruang angkasa untuk mencari rumah baru bagi umat manusia.",
        AgeRating.R13,
        169,
        "Sci-Fi",
    ),
    (
        "High School Musical 3",
        "Para siswa East High menghadapi kelulusan melalui musik dan persahabatan.",
        AgeRating.ALL_AGE,
        112,
        "Family",
    ),
    (
        "Frozen 2",
        "Elsa dan teman-temannya menjelajahi hutan ajaib untuk menemukan asal kekuatannya.",
        AgeRating.ALL_AGE,
        103,
        "Family",
    ),
]

STUDIO_TYPES = [
    ("Regular", 45000),
    ("Premiere", 85000),
    ("IMAX", 120000),
]

STUDIOS = [
    ("Studio 1", "Regular", 8, 10, {(3, 4), (3, 5)}),
    ("Studio 2", "Premiere", 6, 8, {(2, 3), (2, 4)}),
    ("Studio 3", "IMAX", 10, 12, {(4, 5), (4, 6), (5, 5), (5, 6)}),
]

PRODUCTS = [
    ("Popcorn Regular", ProductCategory.FOOD, 30000),
    ("Popcorn Large", ProductCategory.FOOD, 45000),
    ("Iced Tea", ProductCategory.DRINK, 20000),
    ("Cola", ProductCategory.DRINK, 22000),
    ("Couple Combo", ProductCategory.COMBO, 75000),
    ("Movie Poster", ProductCategory.MERCHANDISE, 50000),
    ("Legacy Snack", ProductCategory.FOOD, 15000),
]

SHOWTIME_HOURS = [11, 15, 19]
SHOWTIME_DAYS = 14
