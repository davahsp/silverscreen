import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from .forms import MovieForm, ProductForm, RoleForm, ShowTimeForm, StudioForm
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
from .services.booking import calculate_total, create_online_order, create_onsite_order, parse_addons, unavailable_seat_ids
from .services.cancellation import cancel_order, print_order_tickets
from .services.payments import apply_payment_callback
from .services.scheduling import disable_showtime
from .services.studios import save_studio_layout


ROLE_LABELS = {
    "customer": "Pelanggan",
    "staff": "Staff Counter",
    "scheduler": "Penjadwal",
    "manager": "Manajer",
}


def selected_role(request):
    return request.session.get("role", "customer")


class RoleMixin:
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if self.required_role and selected_role(request) != self.required_role:
            request.session["role"] = self.required_role
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_role"] = selected_role(self.request)
        context["role_labels"] = ROLE_LABELS
        return context


class RoleSwitchView(RoleMixin, FormView):
    form_class = RoleForm
    template_name = "cinema/roles.html"

    def get(self, request, *args, **kwargs):
        role = request.GET.get("role")
        if role in ROLE_LABELS:
            request.session["role"] = role
            return redirect(default_url_for_role(role))
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        role = form.cleaned_data["role"]
        self.request.session["role"] = role
        return redirect(default_url_for_role(role))


def default_url_for_role(role):
    return {
        "customer": "cinema:movies",
        "staff": "cinema:counter_pos",
        "scheduler": "cinema:scheduler_showtimes",
        "manager": "cinema:manager_dashboard",
    }.get(role, "cinema:movies")


class MovieListView(RoleMixin, ListView):
    required_role = "customer"
    model = Movie
    template_name = "cinema/movies.html"
    context_object_name = "movies"

    def get_queryset(self):
        return Movie.objects.filter(is_active=True).select_related("movie_theme")


class MovieDetailView(RoleMixin, DetailView):
    required_role = "customer"
    model = Movie
    template_name = "cinema/movie_detail.html"
    context_object_name = "movie"

    def get_queryset(self):
        return Movie.objects.filter(is_active=True).select_related("movie_theme")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["showtimes"] = ShowTime.objects.filter(
            movie=self.object,
            is_active=True,
            studio__is_active=True,
        ).select_related("studio", "studio__studio_type")
        return context


BOOKING_STEPS = ["Jumlah Tiket", "Pilih Kursi", "Add-ons", "Review", "Pembayaran"]


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
            }
        )
        return context


class BookingQuantityView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_quantity.html"
    current_step = 0

    def post(self, request, *args, **kwargs):
        try:
            quantity = int(request.POST.get("quantity", "0"))
        except ValueError:
            quantity = 0
        if quantity < 1 or quantity > 10:
            messages.error(request, "Jumlah tiket harus 1 sampai 10.")
            return self.get(request, *args, **kwargs)
        draft = self.get_draft()
        if draft.get("quantity") != quantity:
            draft["seat_ids"] = []
        draft["quantity"] = quantity
        self.save_draft(draft)
        return redirect("cinema:booking_seats", showtime_id=self.kwargs["showtime_id"])


class BookingSeatsView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_seats.html"
    current_step = 1

    def dispatch(self, request, *args, **kwargs):
        if not self.get_draft().get("quantity"):
            return redirect("cinema:booking", showtime_id=kwargs["showtime_id"])
        return super().dispatch(request, *args, **kwargs)

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
        quantity = int(draft.get("quantity") or 0)
        try:
            seat_ids = [int(value) for value in request.POST.getlist("seats")]
        except ValueError:
            seat_ids = []
        if len(seat_ids) != quantity:
            messages.error(request, f"Pilih tepat {quantity} kursi.")
            return self.get(request, *args, **kwargs)
        draft["seat_ids"] = seat_ids
        self.save_draft(draft)
        return redirect("cinema:booking_addons", showtime_id=self.kwargs["showtime_id"])


class BookingAddonsView(BookingDraftMixin, TemplateView):
    template_name = "cinema/booking_addons.html"
    current_step = 2

    def dispatch(self, request, *args, **kwargs):
        if not self.get_draft().get("seat_ids"):
            return redirect("cinema:booking_seats", showtime_id=kwargs["showtime_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.filter(is_active=True)
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
    current_step = 3

    def dispatch(self, request, *args, **kwargs):
        draft = self.get_draft()
        if not draft.get("seat_ids"):
            return redirect("cinema:booking_seats", showtime_id=kwargs["showtime_id"])
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
        context["current_step"] = 4
        return context


class OrderListView(RoleMixin, ListView):
    required_role = "customer"
    model = Order
    template_name = "cinema/orders.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.select_related("payment").prefetch_related("tickets__showtime__movie").all()


class OrderDetailView(RoleMixin, DetailView):
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


class OrderCancelView(View):
    def post(self, request, number):
        try:
            cancel_order(number)
            messages.success(request, "Pesanan dibatalkan.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("cinema:order_detail", number=number)


class OrderPrintView(View):
    def post(self, request, number):
        try:
            print_order_tickets(number)
            messages.success(request, "Tiket berhasil dicetak.")
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
        messages.success(request, "Order onsite dibuat dan tiket dicetak.")
        return redirect("cinema:order_detail", number=order.number)


class RefundQueueView(RoleMixin, ListView):
    required_role = "staff"
    model = Payment
    template_name = "cinema/refund_queue.html"
    context_object_name = "payments"

    def get_queryset(self):
        return Payment.objects.filter(status=PaymentStatus.REFUND_PENDING).select_related("order")


class RefundCompleteView(View):
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


class SchedulerShowTimeDisableView(View):
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


class ManagerMovieToggleView(View):
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


class ManagerProductToggleView(View):
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


class ManagerStudioToggleView(View):
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
