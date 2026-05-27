from django.urls import reverse


ROLE_LABELS = {
    "customer": "Pelanggan",
    "staff": "Staff Counter",
    "scheduler": "Penjadwal",
    "manager": "Manajer",
}

ROLE_DEFAULT_URLS = {
    "customer": "cinema:movies",
    "staff": "cinema:counter_pos",
    "scheduler": "cinema:scheduler_showtimes",
    "manager": "cinema:manager_dashboard",
}

ROLE_NAVIGATION = {
    "customer": [
        {"label": "Pilih Film", "target": "cinema:movies"},
        {"label": "Pesanan Saya", "target": "cinema:orders"},
        {"label": "Stub Gateway", "target": "stub_gateway:payments"},
    ],
    "staff": [
        {"label": "Counter POS", "target": "cinema:counter_pos"},
        {"label": "Antrian Refund", "target": "cinema:refund_queue"},
        {"label": "Cari Pesanan", "target": "cinema:order_lookup"},
        {"label": "Stub Gateway", "target": "stub_gateway:payments"},
    ],
    "scheduler": [
        {"label": "Daftar Showtime", "target": "cinema:scheduler_showtimes"},
        {"label": "Jadwalkan", "target": "cinema:scheduler_showtime_new"},
        {"label": "Stub Gateway", "target": "stub_gateway:payments"},
    ],
    "manager": [
        {"label": "Dashboard", "target": "cinema:manager_dashboard"},
        {"label": "Film", "target": "cinema:manager_movies"},
        {"label": "Produk", "target": "cinema:manager_products"},
        {"label": "Studio", "target": "cinema:manager_studios"},
        {"label": "Stub Gateway", "target": "stub_gateway:payments"},
    ],
}


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    cached = getattr(user, "_ss_role", None)
    if cached is not None:
        return cached
    if user.is_superuser:
        role = "manager"
    else:
        role = next(
            (name for name in user.groups.values_list("name", flat=True) if name in ROLE_LABELS),
            None,
        )
    user._ss_role = role
    return role


def default_url_for_role(role):
    return ROLE_DEFAULT_URLS.get(role, "cinema:movies")


def local_view_name(view_name):
    return str(view_name or "").split(":")[-1]


def is_sub_view(current_view_name, target_view_name):
    current = local_view_name(current_view_name)
    target = local_view_name(target_view_name)
    if not current or not target:
        return False
    prefixes = [target]
    if target.endswith("s"):
        prefixes.append(target[:-1])
    return any(current.startswith(f"{prefix}_") for prefix in prefixes)


def build_navigation(role, current_view_name):
    specs = ROLE_NAVIGATION.get(role, [])
    has_exact_match = any(current_view_name == item["target"] for item in specs)
    navigation = []
    for item in specs:
        target = item["target"]
        is_exact = current_view_name == target
        active = is_exact or (not has_exact_match and is_sub_view(current_view_name, target))
        navigation.append(
            {
                "label": item["label"],
                "target": target,
                "url": reverse(target),
                "active": active,
            }
        )
    return navigation
