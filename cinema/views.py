import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, FormView, ListView, RedirectView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from .constants import BOOKING_WINDOW_DAYS
from .forms import CustomerSignupForm, MovieForm, ProductForm, ShowTimeForm, StudioForm
from .models import (
    Movie,
    Order,
    Payment,
    PaymentStatus,
    Product,
    Seat,
    ShowTime,
    Studio,
    TicketStatus,
)
from .navigation import ROLE_LABELS, default_url_for_role, user_role
from .services.booking import (
    SERVICE_CHARGE_PRICE,
    calculate_total,
    create_online_order,
    create_onsite_order,
    parse_addons,
    unavailable_seat_ids,
)
from .services.cancellation import cancel_order, print_order_tickets
from .services.payments import apply_payment_callback
from .services.studios import row_label, save_studio_layout


STUDIO_NOT_EDITABLE_MESSAGE = "Studio nonaktif tidak dapat diedit."
STUDIO_NOT_DEACTIVABLE_MESSAGE = "Studio nonaktif tidak perlu dinonaktifkan."
STUDIO_NOT_RESTORABLE_MESSAGE = "Studio aktif tidak perlu dipulihkan."


def htmx_no_reswap_message(request, message):
    messages.error(request, message)
    response = HttpResponse("")
    response.headers["HX-Reswap"] = "none"
    return response


def booking_window_dates():
    today = timezone.localdate()
    return [today + timedelta(days=offset) for offset in range(BOOKING_WINDOW_DAYS)]


def booking_window_date_range():
    dates = booking_window_dates()
    return dates[0], dates[-1]


def counter_pos_showtimes(now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    current_tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()), current_tz)
    day_end = day_start + timedelta(days=1)
    return (
        ShowTime.objects.filter(
            is_active=True,
            movie__is_active=True,
            studio__is_active=True,
            start_at__gte=day_start,
            start_at__lt=day_end,
            end_at__gt=now,
        )
        .select_related("movie", "studio", "studio__studio_type")
        .order_by("start_at", "movie__title", "studio__name")
    )


def parse_booking_date(value, allowed_dates):
    if not value:
        return None
    try:
        selected_date = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return selected_date if selected_date in allowed_dates else None


def selected_role(request):
    return user_role(getattr(request, "user", None))


def _normalize_allowed_roles(allowed_roles):
    if allowed_roles is None:
        return None
    if isinstance(allowed_roles, str):
        return {allowed_roles}
    return set(allowed_roles)


def _enforce_role(request, allowed_roles):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    role = user_role(request.user)
    normalized_roles = _normalize_allowed_roles(allowed_roles)
    if normalized_roles and role not in normalized_roles:
        if role:
            messages.error(request, "Anda tidak memiliki akses ke halaman tersebut.")
            return redirect(default_url_for_role(role))
        return redirect_to_login(request.get_full_path())
    return None


class IndexView(View):
    def get(self, request, *args, **kwargs):
        role = user_role(request.user)
        return redirect(default_url_for_role(role))


class RoleMixin:
    allowed_roles = None

    def dispatch(self, request, *args, **kwargs):
        if self.allowed_roles:
            denied = _enforce_role(request, self.allowed_roles)
            if denied is not None:
                return denied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = selected_role(self.request)
        context["current_role"] = role
        context["current_role_label"] = ROLE_LABELS.get(role)
        context["role_labels"] = ROLE_LABELS
        return context


class RoleRequiredMixin:
    """For non-template action views (POST endpoints) that need auth + role."""

    allowed_roles = None

    def dispatch(self, request, *args, **kwargs):
        denied = _enforce_role(request, self.allowed_roles)
        if denied is not None:
            return denied
        return super().dispatch(request, *args, **kwargs)


class SingleObjectRequiredMixin(SingleObjectMixin):
    """For action views that operate on one required model object."""


class SilverScreenLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        role = user_role(self.request.user)
        if role:
            return resolve_url(default_url_for_role(role))
        return resolve_url("cinema:movies")


class SilverScreenLogoutView(LogoutView):
    next_page = "cinema:login"


class CustomerSignupView(FormView):
    template_name = "registration/register.html"
    form_class = CustomerSignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(default_url_for_role(user_role(request.user)))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        customer_group, _ = Group.objects.get_or_create(name="customer")
        user.groups.add(customer_group)
        messages.success(self.request, "Akun pelanggan dibuat. Silakan masuk.")
        return redirect(settings.LOGIN_URL)


class MovieListView(RoleMixin, ListView):
    model = Movie
    template_name = "cinema/movies.html"
    context_object_name = "movies"

    def get_queryset(self):
        start_date, end_date = booking_window_date_range()
        active_showtimes = ShowTime.objects.filter(
            movie=OuterRef("pk"),
            is_active=True,
            studio__is_active=True,
            start_at__date__gte=start_date,
            start_at__date__lte=end_date,
        )
        return (
            Movie.objects.filter(is_active=True)
            .annotate(has_bookable_showtime=Exists(active_showtimes))
            .filter(has_bookable_showtime=True)
            .select_related("movie_theme")
        )


class MovieDetailView(RoleMixin, DetailView):
    model = Movie
    template_name = "cinema/movie_detail.html"
    htmx_template_name = "cinema/partials/movie_showtime_list.html"
    context_object_name = "movie"

    def get_queryset(self):
        return Movie.objects.filter(is_active=True).select_related("movie_theme")

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.htmx_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        window_dates = booking_window_dates()
        active_dates = set(
            ShowTime.objects.filter(
                movie=self.object,
                is_active=True,
                studio__is_active=True,
                start_at__date__gte=window_dates[0],
                start_at__date__lte=window_dates[-1],
            )
            .dates("start_at", "day")
        )
        selected_date = parse_booking_date(self.request.GET.get("date"), window_dates)
        if selected_date is None:
            selected_date = min(active_dates) if active_dates else window_dates[0]
        context["showtime_days"] = [
            {
                "date": date,
                "value": date.isoformat(),
                "is_selected": date == selected_date,
                "has_showtimes": date in active_dates,
            }
            for date in window_dates
        ]
        context["selected_showtime_date"] = selected_date
        context["selected_showtime_date_value"] = selected_date.isoformat()
        context["showtime_list_initial_url"] = None
        if self.request.headers.get("HX-Request") != "true":
            context["showtime_list_initial_url"] = self.request.path
        context["booking_window_days"] = BOOKING_WINDOW_DAYS
        context["showtimes"] = ShowTime.objects.filter(
            movie=self.object,
            is_active=True,
            studio__is_active=True,
            start_at__date=selected_date,
        ).select_related("studio", "studio__studio_type")
        return context


BOOKING_STEPS = ["Pilih Kursi", "Add-ons", "Review", "Pembayaran"]


class BookingDraftMixin(RoleMixin):
    allowed_roles = "customer"

    def get_showtime(self):
        return get_object_or_404(
            ShowTime.objects.select_related("movie", "studio", "studio__studio_type"),
            pk=self.kwargs["showtime_id"],
            is_active=True,
        )

    def draft_key(self):
        return f"booking_{self.kwargs['showtime_id']}"

    def get_draft(self):
        return self.request.session.get(self.draft_key(), {})

    def save_draft(self, draft):
        self.request.session[self.draft_key()] = draft
        self.request.session.modified = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        showtime = self.get_showtime()
        context.update(
            {
                "showtime": showtime,
                "booking_steps": BOOKING_STEPS,
                "current_step": getattr(self, "current_step", 0),
                "draft": self.get_draft(),
                "service_charge_price": SERVICE_CHARGE_PRICE,
                "max_ticket_quantity": Order.MAX_TICKETS,
            }
        )
        return context


class BookingSeatsView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_seats.html"
    current_step = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        showtime = context["showtime"]
        unavailable = unavailable_seat_ids(showtime)
        seats = Seat.objects.filter(studio=showtime.studio).order_by("grid_y_pos", "grid_x_pos")
        context.update(
            {
                "seats": seats,
                "seat_layout": build_interactive_studio_seat_layout(showtime.studio, seats),
                "occupancy": {seat_id: TicketStatus.HELD for seat_id in unavailable},
                "selected_seat_ids": [int(value) for value in context["draft"].get("seat_ids", [])],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        draft = self.get_draft()
        try:
            seat_ids = [int(value) for value in request.POST.getlist("seats")]
        except ValueError:
            seat_ids = []
        if len(seat_ids) < 1 or len(seat_ids) > Order.MAX_TICKETS:
            messages.error(request, f"Pilih 1 sampai {Order.MAX_TICKETS} kursi.")
            return self.get(request, *args, **kwargs)
        draft["seat_ids"] = seat_ids
        draft["quantity"] = len(seat_ids)
        self.save_draft(draft)
        return redirect("cinema:booking_addons", showtime_id=self.kwargs["showtime_id"])


class BookingAddonsView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_addons.html"
    current_step = 1

    def dispatch(self, request, *args, **kwargs):
        if not self.get_draft().get("seat_ids"):
            return redirect("cinema:booking", showtime_id=kwargs["showtime_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket_quantity = len(context["draft"].get("seat_ids", []))
        context["products"] = Product.objects.filter(is_active=True)
        context["ticket_quantity"] = ticket_quantity
        context["ticket_subtotal"] = context["showtime"].price * ticket_quantity
        context["addon_quantities"] = {
            str(product_id): quantity for product_id, quantity in context["draft"].get("addons", [])
        }
        return context

    def post(self, request, *args, **kwargs):
        draft = self.get_draft()
        draft["addons"] = parse_addons(request.POST)
        self.save_draft(draft)
        return redirect("cinema:booking_review", showtime_id=self.kwargs["showtime_id"])


class BookingReviewView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_review.html"
    current_step = 2

    def dispatch(self, request, *args, **kwargs):
        draft = self.get_draft()
        if not draft.get("seat_ids"):
            return redirect("cinema:booking", showtime_id=kwargs["showtime_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        showtime = context["showtime"]
        draft = context["draft"]
        seat_ids = draft.get("seat_ids", [])
        addons = draft.get("addons", [])
        products = Product.objects.in_bulk([product_id for product_id, _quantity in addons])
        addon_lines = []
        for product_id, quantity in addons:
            product = products.get(product_id)
            if product and product.is_active:
                addon_lines.append({"product": product, "quantity": quantity, "total": product.price * quantity})
        seats = Seat.objects.filter(id__in=seat_ids).order_by("grid_y_pos", "grid_x_pos")
        context.update(
            {
                "selected_seats": seats,
                "addon_lines": addon_lines,
                "ticket_subtotal": showtime.price * len(seat_ids),
                "total": calculate_total(showtime, seats, addons),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        showtime = self.get_showtime()
        draft = self.get_draft()
        try:
            order = create_online_order(
                showtime.id,
                draft.get("seat_ids", []),
                draft.get("addons", []),
                customer=request.user,
            )
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            return self.get(request, *args, **kwargs)
        messages.success(request, "Pesanan online dibuat. Lanjutkan pembayaran melalui stub gateway.")
        self.request.session.pop(self.draft_key(), None)
        return redirect("cinema:booking_payment", number=order.number)


class BookingPaymentView(RoleMixin, DetailView):
    allowed_roles = "customer"
    model = Order
    slug_field = "number"
    slug_url_kwarg = "number"
    template_name = "cinema/booking_payment.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.select_related("payment").prefetch_related("tickets__showtime__movie", "tickets__seat")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["booking_steps"] = BOOKING_STEPS
        context["current_step"] = 3
        return context


class OrderListView(RoleMixin, TemplateView):
    allowed_roles = {"customer", "staff"}
    template_name = "cinema/orders.html"

    def get_order_page_context(self):
        if selected_role(self.request) == "staff":
            return {
                "page_title": "Daftar Pesanan",
                "page_subtitle": "Semua pesanan online dan onsite.",
            }
        return {
            "page_title": "Pesanan Saya",
            "page_subtitle": "Status pesanan online dan onsite Anda.",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_order_page_context())
        context.update(
            {
                "order_id_filter": self.request.GET.get("order_id", "").strip(),
                "movie_name_filter": self.request.GET.get("movie_name", "").strip(),
                "date_filter": self.request.GET.get("date", "").strip(),
            }
        )
        return context


class OrderTablePartialView(RoleMixin, ListView):
    allowed_roles = {"customer", "staff"}
    model = Order
    template_name = "cinema/partials/order_table.html"
    context_object_name = "orders"

    def get_queryset(self):
        queryset = Order.objects.select_related("payment", "customer").prefetch_related("tickets__showtime__movie")
        role = selected_role(self.request)
        if role == "customer":
            queryset = queryset.filter(customer=self.request.user)

        order_id = self.request.GET.get("order_id", "").strip()
        movie_name = self.request.GET.get("movie_name", "").strip()
        date_value = self.request.GET.get("date", "").strip()

        if order_id:
            queryset = queryset.filter(number__icontains=order_id)
        if movie_name:
            queryset = queryset.filter(tickets__showtime__movie__title__icontains=movie_name)
        if date_value:
            try:
                selected_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                selected_date = None
            if selected_date is not None:
                queryset = queryset.filter(tickets__showtime__start_at__date=selected_date)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_order_filters"] = any(
            self.request.GET.get(name, "").strip() for name in ("order_id", "movie_name", "date")
        )
        return context


class OrderDetailView(LoginRequiredMixin, RoleMixin, DetailView):
    model = Order
    slug_field = "number"
    slug_url_kwarg = "number"
    template_name = "cinema/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.select_related("payment").prefetch_related(
            "tickets__showtime__movie",
            "tickets__showtime__studio",
            "tickets__seat",
            "addons__product",
            "charges",
        )


class OrderCancelView(RoleRequiredMixin, SingleObjectRequiredMixin, View):
    allowed_roles = {"customer", "staff"}
    model = Order

    def get_queryset(self):
        queryset = Order.objects.all()
        groups = set(self.request.user.groups.values_list("name", flat=True))
        if "customer" in groups and "staff" not in groups:
            queryset = queryset.filter(customer=self.request.user)
        return queryset

    def post(self, request, pk):
        order = self.get_object()
        try:
            cancel_order(order)
            messages.success(request, "Pesanan dibatalkan.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("cinema:order_detail", number=order.number)


class OrderPrintView(LoginRequiredMixin, View):
    def post(self, request, number):
        try:
            print_order_tickets(number)
            messages.success(request, "Tiket siap dicetak.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("cinema:order_detail", number=number)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            payment = apply_payment_callback(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return JsonResponse({"ok": False, "error": message}, status=400)
        return JsonResponse({"ok": True, "payment": payment.internal_payment_id, "status": payment.status})


class CounterPOSView(RoleMixin, TemplateView):
    allowed_roles = "staff"
    template_name = "cinema/staff_pos.html"
    htmx_template_name = "cinema/partials/staff_pos_seat_map.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.htmx_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        showtime_id = self.request.GET.get("showtime") or self.request.POST.get("showtime")
        selected_customer_id = self.request.POST.get("customer") or self.request.GET.get("customer")
        customers = User.objects.filter(groups__name="customer").order_by("username").distinct()
        available_showtimes = counter_pos_showtimes()
        selected_customer = None
        if selected_customer_id and selected_customer_id.isdigit():
            selected_customer = customers.filter(pk=int(selected_customer_id)).first()
        showtime = None
        seats = []
        occupancy = {}
        if showtime_id:
            showtime = get_object_or_404(available_showtimes, pk=showtime_id)
            seats = Seat.objects.filter(studio=showtime.studio).order_by("grid_y_pos", "grid_x_pos")
            occupancy = {seat_id: TicketStatus.HELD for seat_id in unavailable_seat_ids(showtime)}
        context.update(
            {
                "showtimes": available_showtimes,
                "showtime": showtime,
                "seats": seats,
                "seat_layout": build_interactive_studio_seat_layout(showtime.studio, seats) if showtime else [],
                "products": Product.objects.filter(is_active=True),
                "customers": customers,
                "selected_customer": selected_customer,
                "selected_customer_id": int(selected_customer_id) if selected_customer_id and selected_customer_id.isdigit() else None,
                "occupancy": occupancy,
                "max_ticket_quantity": Order.MAX_TICKETS,
            }
        )
        return context

    def get_selected_customer(self):
        raw_customer_id = self.request.POST.get("customer", "")
        if not raw_customer_id:
            return None
        try:
            customer_id = int(raw_customer_id)
        except ValueError as exc:
            raise ValidationError("Customer tidak valid.") from exc
        customer = User.objects.filter(pk=customer_id, groups__name="customer").first()
        if customer is None:
            raise ValidationError("Customer tidak valid.")
        return customer

    def post(self, request, *args, **kwargs):
        try:
            showtime_id = int(request.POST["showtime"])
            if not counter_pos_showtimes().filter(pk=showtime_id).exists():
                raise ValidationError("Jam tayang tidak tersedia untuk penjualan counter.")
            seat_ids = [int(value) for value in request.POST.getlist("seats")]
            order = create_onsite_order(
                showtime_id,
                seat_ids,
                parse_addons(request.POST),
                customer=self.get_selected_customer(),
            )
        except (KeyError, ValueError, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            return self.get(request, *args, **kwargs)
        messages.success(request, "Order onsite dibuat. Tiket siap dicetak.")
        return redirect("cinema:order_detail", number=order.number)


class RefundQueueView(RoleMixin, ListView):
    allowed_roles = "staff"
    model = Payment
    template_name = "cinema/refund_queue.html"
    context_object_name = "payments"

    def get_queryset(self):
        return Payment.objects.filter(status=PaymentStatus.REFUND_PENDING).select_related("order")


class RefundCompleteView(RoleRequiredMixin, View):
    allowed_roles = "staff"

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, status=PaymentStatus.REFUND_PENDING)
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status"])
        messages.success(request, "Refund ditandai selesai.")
        return redirect("cinema:refund_queue")


class OrderLookupView(RoleRequiredMixin, RedirectView):
    allowed_roles = "staff"
    pattern_name = "cinema:orders"


class SchedulerShowTimeListView(RoleMixin, ListView):
    allowed_roles = "scheduler"
    model = ShowTime
    template_name = "cinema/scheduler_showtimes.html"
    context_object_name = "showtimes"
    queryset = ShowTime.objects.select_related("movie", "studio", "studio__studio_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        showtimes = list(context["showtimes"])
        ongoing = [showtime for showtime in showtimes if showtime.start_at <= now <= showtime.end_at]
        scheduled = [showtime for showtime in showtimes if now < showtime.start_at]
        ended = [showtime for showtime in showtimes if showtime.end_at < now]
        context["showtime_tabs"] = [
            {
                "id": "ongoing",
                "label": "Sedang Berlangsung",
                "showtimes": sorted(ongoing, key=lambda item: item.end_at),
            },
            {
                "id": "scheduled",
                "label": "Terjadwal",
                "showtimes": sorted(scheduled, key=lambda item: item.start_at),
            },
            {
                "id": "ended",
                "label": "Selesai",
                "showtimes": sorted(ended, key=lambda item: item.end_at, reverse=True),
            },
        ]
        return context


class SchedulerShowTimeCreateView(RoleMixin, FormView):
    allowed_roles = "scheduler"
    form_class = ShowTimeForm
    template_name = "cinema/showtime_form.html"
    success_url = reverse_lazy("cinema:scheduler_showtimes")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movies = Movie.objects.filter(is_active=True).select_related("movie_theme").order_by("title")
        studios = Studio.objects.filter(is_active=True).select_related("studio_type").order_by("name")
        showtimes = ShowTime.objects.filter(is_active=True).select_related("movie", "studio")
        context["scheduler_wizard_data"] = {
            "movies": [
                {
                    "id": movie.id,
                    "title": movie.title,
                    "theme": movie.movie_theme.name,
                    "age_rating_display": movie.get_age_rating_display(),
                    "runtime_minutes": movie.runtime_minutes,
                    "main_picture_url": movie.main_picture.url if movie.main_picture else "",
                }
                for movie in movies
            ],
            "studios": [
                {
                    "id": studio.id,
                    "name": studio.name,
                    "studio_type": studio.studio_type.name,
                    "base_price": studio.studio_type.base_price,
                    "capacity": studio.capacity,
                }
                for studio in studios
            ],
            "showtimes": [
                {
                    "id": showtime.id,
                    "movie_title": showtime.movie.title,
                    "studio_id": showtime.studio_id,
                    "start_at": timezone.localtime(showtime.start_at).isoformat(),
                    "end_at": timezone.localtime(showtime.end_at).isoformat(),
                }
                for showtime in showtimes
            ],
            "today": timezone.localdate().isoformat(),
            "now": timezone.localtime().isoformat(),
        }
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Jam tayang dibuat.")
        return super().form_valid(form)


class ManagerDashboardView(RoleMixin, TemplateView):
    allowed_roles = "manager"
    template_name = "cinema/manager_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "movie_count": Movie.objects.count(),
                "product_count": Product.objects.count(),
                "studio_count": Studio.objects.count(),
                "showtime_count": ShowTime.objects.count(),
            }
        )
        return context


class ManagerMovieListView(RoleMixin, ListView):
    allowed_roles = "manager"
    model = Movie
    template_name = "cinema/manager_movies.html"
    context_object_name = "movies"
    queryset = Movie.objects.select_related("movie_theme")


class ManagerMovieCreateView(RoleMixin, CreateView):
    allowed_roles = "manager"
    model = Movie
    form_class = MovieForm
    template_name = "cinema/manager_movie_form.html"
    success_url = reverse_lazy("cinema:manager_movies")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        main_picture = form.cleaned_data.get("main_picture")
        self.object.main_picture = None
        self.object.save()
        if main_picture:
            self.object.main_picture = main_picture
            self.object.save(update_fields=["main_picture"])
        return redirect(self.success_url)


class ManagerMovieDetailView(RoleMixin, DetailView):
    allowed_roles = "manager"
    model = Movie
    template_name = "cinema/manager_movie_detail.html"
    context_object_name = "movie"
    queryset = Movie.objects.select_related("movie_theme")


class ManagerMovieDetailPartialView(ManagerMovieDetailView):
    template_name = "cinema/partials/manager_movie_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update_mode"] = self.request.GET.get("mode") == "update"
        context["form"] = MovieForm(instance=self.object)
        return context


class ManagerMovieUpdateView(RoleMixin, UpdateView):
    allowed_roles = "manager"
    model = Movie
    form_class = MovieForm
    template_name = "cinema/object_form.html"
    context_object_name = "movie"

    def get_queryset(self):
        return Movie.objects.select_related("movie_theme")

    def get_success_url(self):
        return reverse("cinema:manager_movie_detail", args=[self.object.pk])

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            context = self.get_context_data(form=MovieForm(instance=self.object), update_mode=False)
            return render(self.request, "cinema/partials/manager_movie_detail.html", context)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            context = self.get_context_data(form=form, update_mode=True)
            return render(self.request, "cinema/partials/manager_movie_detail.html", context)
        return super().form_invalid(form)


class ManagerMovieToggleView(RoleRequiredMixin, View):
    allowed_roles = "manager"

    def post(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        movie.is_active = not movie.is_active
        movie.save(update_fields=["is_active"])
        return redirect("cinema:manager_movies")


class ManagerProductListView(RoleMixin, ListView):
    allowed_roles = "manager"
    model = Product
    template_name = "cinema/manager_products.html"
    context_object_name = "products"


class ManagerProductCreateView(RoleMixin, CreateView):
    allowed_roles = "manager"
    model = Product
    form_class = ProductForm
    template_name = "cinema/manager_product_form.html"
    success_url = reverse_lazy("cinema:manager_products")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        picture = form.cleaned_data.get("picture")
        self.object.picture = None
        self.object.save()
        if picture:
            self.object.picture = picture
            self.object.save(update_fields=["picture"])
        return redirect(self.success_url)


class ManagerProductDetailView(RoleMixin, DetailView):
    allowed_roles = "manager"
    model = Product
    template_name = "cinema/manager_product_detail.html"
    context_object_name = "product"


class ManagerProductDetailPartialView(ManagerProductDetailView):
    template_name = "cinema/partials/manager_product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update_mode"] = self.request.GET.get("mode") == "update"
        context["form"] = ProductForm(instance=self.object)
        return context


class ManagerProductUpdateView(RoleMixin, UpdateView):
    allowed_roles = "manager"
    model = Product
    form_class = ProductForm
    template_name = "cinema/object_form.html"
    context_object_name = "product"

    def get_success_url(self):
        return reverse("cinema:manager_product_detail", args=[self.object.pk])

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            context = self.get_context_data(form=ProductForm(instance=self.object), update_mode=False)
            return render(self.request, "cinema/partials/manager_product_detail.html", context)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            context = self.get_context_data(form=form, update_mode=True)
            return render(self.request, "cinema/partials/manager_product_detail.html", context)
        return super().form_invalid(form)


class ManagerProductToggleView(RoleRequiredMixin, View):
    allowed_roles = "manager"

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])
        return redirect("cinema:manager_products")


class ManagerStudioListView(RoleMixin, ListView):
    allowed_roles = "manager"
    model = Studio
    template_name = "cinema/manager_studios.html"
    context_object_name = "studios"

    def get_queryset(self):
        return Studio.objects.filter(is_active=True).select_related("studio_type").prefetch_related("seats")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Studio",
                "page_subtitle": "Studio aktif yang dapat dipakai untuk jam tayang.",
                "empty_message": "Belum ada studio aktif.",
                "show_inactive_link": True,
            }
        )
        return context


class ManagerInactiveStudioListView(RoleMixin, ListView):
    allowed_roles = "manager"
    model = Studio
    template_name = "cinema/manager_studios.html"
    context_object_name = "studios"

    def get_queryset(self):
        return Studio.objects.filter(is_active=False).select_related("studio_type").prefetch_related("seats")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Studio Nonaktif",
                "page_subtitle": "Studio yang sedang tidak tersedia untuk penjadwalan.",
                "empty_message": "Belum ada studio nonaktif.",
                "show_back_to_active": True,
            }
        )
        return context


class ManagerStudioDetailView(RoleMixin, DetailView):
    allowed_roles = "manager"
    model = Studio
    template_name = "cinema/manager_studio_detail.html"
    context_object_name = "studio"
    queryset = Studio.objects.select_related("studio_type").prefetch_related("seats")


DEFAULT_STUDIO_LAYOUT_ROWS = 10
DEFAULT_STUDIO_LAYOUT_COLS = 15


def build_studio_layout_rows(rows, cols, active_positions):
    return [
        [
            {
                "x": x,
                "y": y,
                "value": f"{y},{x}",
                "label": f"{row_label(y)}{x + 1}",
                "active": (y, x) in active_positions,
            }
            for x in range(cols)
        ]
        for y in range(rows)
    ]


def build_readonly_studio_layout(studio):
    seats_by_position = {(seat.grid_y_pos, seat.grid_x_pos): seat for seat in studio.seats.all()}
    return [
        [
            {
                "x": x,
                "y": y,
                "label": seats_by_position[(y, x)].number if (y, x) in seats_by_position else "",
                "active": (y, x) in seats_by_position,
            }
            for x in range(studio.grid_cols)
        ]
        for y in range(studio.grid_rows)
    ]


def build_interactive_studio_seat_layout(studio, seats):
    seats_by_position = {(seat.grid_y_pos, seat.grid_x_pos): seat for seat in seats}
    return [
        [
            {
                "x": x,
                "y": y,
                "seat": seats_by_position.get((y, x)),
            }
            for x in range(studio.grid_cols)
        ]
        for y in range(studio.grid_rows)
    ]


def parse_layout_grid(post_data):
    positions = parse_layout_positions(post_data)
    try:
        rows = int(post_data.get("layout_rows", ""))
        cols = int(post_data.get("layout_cols", ""))
    except ValueError:
        rows = 0
        cols = 0
    if rows < 1:
        rows = max((y for y, _x in positions), default=-1) + 1
    if cols < 1:
        cols = max((x for _y, x in positions), default=-1) + 1
    return rows, cols, positions


class ManagerStudioLayoutMixin:
    def get_layout_state(self):
        if self.request.method == "POST":
            rows, cols, positions = parse_layout_grid(self.request.POST)
            return rows or DEFAULT_STUDIO_LAYOUT_ROWS, cols or DEFAULT_STUDIO_LAYOUT_COLS, positions
        if getattr(self, "object", None) and self.object.pk:
            positions = set(self.object.seats.values_list("grid_y_pos", "grid_x_pos"))
            return self.object.grid_rows, self.object.grid_cols, positions
        rows = DEFAULT_STUDIO_LAYOUT_ROWS
        cols = DEFAULT_STUDIO_LAYOUT_COLS
        return rows, cols, {(y, x) for y in range(rows) for x in range(cols)}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows, cols, positions = self.get_layout_state()
        context.update(
            {
                "layout_rows": rows,
                "layout_cols": cols,
                "layout_capacity": len(positions),
                "layout_grid": build_studio_layout_rows(rows, cols, positions),
                "studio_form_title": "Edit Studio" if getattr(self, "object", None) and self.object.pk else "Tambah Studio",
            }
        )
        return context


class ManagerStudioFormTitleMixin:
    studio_form_title = "Studio"
    show_layout_builder = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["studio_form_title"] = self.studio_form_title
        context["show_layout_builder"] = self.show_layout_builder
        studio = getattr(self, "object", None)
        if studio and studio.pk and not self.show_layout_builder:
            context.update(
                {
                    "layout_rows": studio.grid_rows,
                    "layout_cols": studio.grid_cols,
                    "layout_capacity": studio.capacity,
                    "layout_grid": build_readonly_studio_layout(studio),
                }
            )
        return context


class ManagerStudioDetailPartialView(ManagerStudioDetailView):
    template_name = "cinema/partials/manager_studio_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        update_mode = self.request.GET.get("mode") == "update"
        context["update_mode"] = update_mode
        context["form"] = StudioForm(instance=self.object)
        context.update(
            {
                "layout_rows": self.object.grid_rows,
                "layout_cols": self.object.grid_cols,
                "layout_capacity": self.object.capacity,
                "layout_grid": build_readonly_studio_layout(self.object),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.GET.get("mode") == "update" and not self.object.is_editable:
            return htmx_no_reswap_message(request, STUDIO_NOT_EDITABLE_MESSAGE)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class ManagerStudioCreateView(ManagerStudioLayoutMixin, ManagerStudioFormTitleMixin, RoleMixin, CreateView):
    allowed_roles = "manager"
    model = Studio
    form_class = StudioForm
    template_name = "cinema/studio_form.html"
    success_url = reverse_lazy("cinema:manager_studios")
    studio_form_title = "Tambah Studio"
    show_layout_builder = True

    def form_valid(self, form):
        studio = form.save(commit=False)
        rows, cols, positions = parse_layout_grid(self.request.POST)
        studio.grid_rows = rows
        studio.grid_cols = cols
        try:
            save_studio_layout(studio, positions)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return redirect(self.success_url)


class ManagerStudioUpdateView(ManagerStudioFormTitleMixin, RoleMixin, UpdateView):
    allowed_roles = "manager"
    model = Studio
    form_class = StudioForm
    template_name = "cinema/studio_form.html"
    studio_form_title = "Edit Studio"

    def get_queryset(self):
        return Studio.objects.select_related("studio_type").prefetch_related("seats")

    def get_success_url(self):
        return reverse("cinema:manager_studio_detail", args=[self.object.pk])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return redirect(self.get_success_url())

    def form_valid(self, form):
        if not self.object.is_editable:
            return htmx_no_reswap_message(self.request, STUDIO_NOT_EDITABLE_MESSAGE)
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            context = self.get_context_data(form=StudioForm(instance=self.object), update_mode=False)
            context.update(
                {
                    "studio": self.object,
                    "layout_rows": self.object.grid_rows,
                    "layout_cols": self.object.grid_cols,
                    "layout_capacity": self.object.capacity,
                    "layout_grid": build_readonly_studio_layout(self.object),
                }
            )
            return render(self.request, "cinema/partials/manager_studio_detail.html", context)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if not self.object.is_editable:
            return htmx_no_reswap_message(self.request, STUDIO_NOT_EDITABLE_MESSAGE)
        if self.request.headers.get("HX-Request") == "true":
            self.object = self.get_object()
            context = self.get_context_data(form=form, update_mode=True)
            context.update(
                {
                    "studio": self.object,
                    "layout_rows": self.object.grid_rows,
                    "layout_cols": self.object.grid_cols,
                    "layout_capacity": self.object.capacity,
                    "layout_grid": build_readonly_studio_layout(self.object),
                }
            )
            return render(self.request, "cinema/partials/manager_studio_detail.html", context)
        return super().form_invalid(form)


class ManagerStudioToggleView(RoleRequiredMixin, View):
    allowed_roles = "manager"

    def post(self, request, pk):
        studio = get_object_or_404(Studio.objects.select_related("studio_type").prefetch_related("seats"), pk=pk)
        if not studio.is_deactivable:
            return htmx_no_reswap_message(request, STUDIO_NOT_DEACTIVABLE_MESSAGE)
        studio.is_active = False
        studio.save(update_fields=["is_active"])
        if request.headers.get("HX-Request") == "true":
            context = {
                "studio": studio,
                "update_mode": False,
                "form": StudioForm(instance=studio),
                "layout_rows": studio.grid_rows,
                "layout_cols": studio.grid_cols,
                "layout_capacity": studio.capacity,
                "layout_grid": build_readonly_studio_layout(studio),
            }
            return render(request, "cinema/partials/manager_studio_detail.html", context)
        return redirect("cinema:manager_studio_detail", pk=studio.pk)


class ManagerStudioRestoreView(RoleRequiredMixin, View):
    allowed_roles = "manager"

    def post(self, request, pk):
        studio = get_object_or_404(Studio.objects.select_related("studio_type").prefetch_related("seats"), pk=pk)
        if not studio.is_restorable:
            return htmx_no_reswap_message(request, STUDIO_NOT_RESTORABLE_MESSAGE)
        studio.is_active = True
        studio.save(update_fields=["is_active"])
        if request.headers.get("HX-Request") == "true":
            context = {
                "studio": studio,
                "update_mode": False,
                "form": StudioForm(instance=studio),
                "layout_rows": studio.grid_rows,
                "layout_cols": studio.grid_cols,
                "layout_capacity": studio.capacity,
                "layout_grid": build_readonly_studio_layout(studio),
            }
            return render(request, "cinema/partials/manager_studio_detail.html", context)
        return redirect("cinema:manager_studio_detail", pk=studio.pk)


def parse_layout_positions(post_data):
    positions = set()
    for value in post_data.getlist("seat_cells"):
        try:
            y, x = value.split(",")
            positions.add((int(y), int(x)))
        except ValueError:
            continue
    return positions
