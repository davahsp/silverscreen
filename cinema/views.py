import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, resolve_url
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

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
from .services.scheduling import disable_showtime
from .services.studios import save_studio_layout


def booking_window_dates():
    today = timezone.localdate()
    return [today + timedelta(days=offset) for offset in range(BOOKING_WINDOW_DAYS)]


def booking_window_date_range():
    dates = booking_window_dates()
    return dates[0], dates[-1]


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


def _enforce_role(request, required_role):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    role = user_role(request.user)
    if required_role and role != required_role:
        if role:
            messages.error(request, "Anda tidak memiliki akses ke halaman tersebut.")
            return redirect(default_url_for_role(role))
        return redirect_to_login(request.get_full_path())
    return None


class RoleMixin:
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if self.required_role:
            denied = _enforce_role(request, self.required_role)
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

    required_role = None

    def dispatch(self, request, *args, **kwargs):
        denied = _enforce_role(request, self.required_role)
        if denied is not None:
            return denied
        return super().dispatch(request, *args, **kwargs)


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
    required_role = "customer"

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
        context.update(
            {
                "seats": Seat.objects.filter(studio=showtime.studio).order_by("grid_y_pos", "grid_x_pos"),
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
            order = create_online_order(showtime.id, draft.get("seat_ids", []), draft.get("addons", []))
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            return self.get(request, *args, **kwargs)
        messages.success(request, "Pesanan online dibuat. Lanjutkan pembayaran melalui stub gateway.")
        self.request.session.pop(self.draft_key(), None)
        return redirect("cinema:booking_payment", number=order.number)


class BookingPaymentView(RoleMixin, DetailView):
    required_role = "customer"
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


class OrderListView(RoleMixin, ListView):
    required_role = "customer"
    model = Order
    template_name = "cinema/orders.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.select_related("payment").prefetch_related("tickets__showtime__movie").all()


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


class OrderCancelView(RoleRequiredMixin, View):
    required_role = "customer"

    def post(self, request, number):
        try:
            cancel_order(number)
            messages.success(request, "Pesanan dibatalkan.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("cinema:order_detail", number=number)


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
    required_role = "staff"
    template_name = "cinema/staff_pos.html"
    htmx_template_name = "cinema/partials/staff_pos_seat_map.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.htmx_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        showtime_id = self.request.GET.get("showtime") or self.request.POST.get("showtime")
        showtime = None
        seats = []
        occupancy = {}
        if showtime_id:
            showtime = get_object_or_404(ShowTime.objects.select_related("movie", "studio"), pk=showtime_id, is_active=True)
            seats = Seat.objects.filter(studio=showtime.studio).order_by("grid_y_pos", "grid_x_pos")
            occupancy = {seat_id: TicketStatus.HELD for seat_id in unavailable_seat_ids(showtime)}
        context.update(
            {
                "showtimes": ShowTime.objects.filter(is_active=True).select_related("movie", "studio"),
                "showtime": showtime,
                "seats": seats,
                "products": Product.objects.filter(is_active=True),
                "occupancy": occupancy,
                "max_ticket_quantity": Order.MAX_TICKETS,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        try:
            showtime_id = int(request.POST["showtime"])
            seat_ids = [int(value) for value in request.POST.getlist("seats")]
            order = create_onsite_order(showtime_id, seat_ids, parse_addons(request.POST))
        except (KeyError, ValueError, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            return self.get(request, *args, **kwargs)
        messages.success(request, "Order onsite dibuat. Tiket siap dicetak.")
        return redirect("cinema:order_detail", number=order.number)


class RefundQueueView(RoleMixin, ListView):
    required_role = "staff"
    model = Payment
    template_name = "cinema/refund_queue.html"
    context_object_name = "payments"

    def get_queryset(self):
        return Payment.objects.filter(status=PaymentStatus.REFUND_PENDING).select_related("order")


class RefundCompleteView(RoleRequiredMixin, View):
    required_role = "staff"

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, status=PaymentStatus.REFUND_PENDING)
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status"])
        messages.success(request, "Refund ditandai selesai.")
        return redirect("cinema:refund_queue")


class OrderLookupView(RoleMixin, TemplateView):
    required_role = "staff"
    template_name = "cinema/order_lookup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "")
        context["q"] = q
        context["orders"] = Order.objects.filter(number__icontains=q)[:20] if q else []
        return context


class SchedulerShowTimeListView(RoleMixin, ListView):
    required_role = "scheduler"
    model = ShowTime
    template_name = "cinema/scheduler_showtimes.html"
    context_object_name = "showtimes"
    queryset = ShowTime.objects.select_related("movie", "studio", "studio__studio_type")


class SchedulerShowTimeCreateView(RoleMixin, FormView):
    required_role = "scheduler"
    form_class = ShowTimeForm
    template_name = "cinema/showtime_form.html"
    success_url = reverse_lazy("cinema:scheduler_showtimes")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Showtime dibuat.")
        return super().form_valid(form)


class SchedulerShowTimeUpdateView(SchedulerShowTimeCreateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(ShowTime, pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Showtime diperbarui.")
        return redirect(self.success_url)


class SchedulerShowTimeDisableView(RoleRequiredMixin, View):
    required_role = "scheduler"

    def post(self, request, pk):
        try:
            disable_showtime(pk)
            messages.success(request, "Showtime dinonaktifkan.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("cinema:scheduler_showtimes")


class ManagerDashboardView(RoleMixin, TemplateView):
    required_role = "manager"
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
    required_role = "manager"
    model = Movie
    template_name = "cinema/manager_movies.html"
    context_object_name = "movies"
    queryset = Movie.objects.select_related("movie_theme")


class ManagerMovieCreateView(RoleMixin, CreateView):
    required_role = "manager"
    model = Movie
    form_class = MovieForm
    template_name = "cinema/object_form.html"
    success_url = reverse_lazy("cinema:manager_movies")


class ManagerMovieUpdateView(RoleMixin, UpdateView):
    required_role = "manager"
    model = Movie
    form_class = MovieForm
    template_name = "cinema/object_form.html"
    success_url = reverse_lazy("cinema:manager_movies")


class ManagerMovieToggleView(RoleRequiredMixin, View):
    required_role = "manager"

    def post(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        movie.is_active = not movie.is_active
        movie.save(update_fields=["is_active"])
        return redirect("cinema:manager_movies")


class ManagerProductListView(RoleMixin, ListView):
    required_role = "manager"
    model = Product
    template_name = "cinema/manager_products.html"
    context_object_name = "products"


class ManagerProductCreateView(RoleMixin, CreateView):
    required_role = "manager"
    model = Product
    form_class = ProductForm
    template_name = "cinema/object_form.html"
    success_url = reverse_lazy("cinema:manager_products")


class ManagerProductUpdateView(RoleMixin, UpdateView):
    required_role = "manager"
    model = Product
    form_class = ProductForm
    template_name = "cinema/object_form.html"
    success_url = reverse_lazy("cinema:manager_products")


class ManagerProductToggleView(RoleRequiredMixin, View):
    required_role = "manager"

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])
        return redirect("cinema:manager_products")


class ManagerStudioListView(RoleMixin, ListView):
    required_role = "manager"
    model = Studio
    template_name = "cinema/manager_studios.html"
    context_object_name = "studios"
    queryset = Studio.objects.select_related("studio_type").prefetch_related("seats")


class ManagerStudioCreateView(RoleMixin, CreateView):
    required_role = "manager"
    model = Studio
    form_class = StudioForm
    template_name = "cinema/studio_form.html"
    success_url = reverse_lazy("cinema:manager_studios")

    def form_valid(self, form):
        studio = form.save(commit=False)
        positions = parse_layout_positions(self.request.POST)
        try:
            save_studio_layout(studio, positions)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return redirect(self.success_url)


class ManagerStudioUpdateView(RoleMixin, UpdateView):
    required_role = "manager"
    model = Studio
    form_class = StudioForm
    template_name = "cinema/studio_form.html"
    success_url = reverse_lazy("cinema:manager_studios")

    def form_valid(self, form):
        studio = form.save(commit=False)
        positions = parse_layout_positions(self.request.POST)
        try:
            save_studio_layout(studio, positions)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return redirect(self.success_url)


class ManagerStudioToggleView(RoleRequiredMixin, View):
    required_role = "manager"

    def post(self, request, pk):
        studio = get_object_or_404(Studio, pk=pk)
        studio.is_active = not studio.is_active
        studio.save(update_fields=["is_active"])
        return redirect("cinema:manager_studios")


def parse_layout_positions(post_data):
    positions = set()
    for value in post_data.getlist("seat_cells"):
        try:
            y, x = value.split(",")
            positions.add((int(y), int(x)))
        except ValueError:
            continue
    return positions
