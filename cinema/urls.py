from django.urls import path

from . import views

app_name = "cinema"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("login/", views.SilverScreenLoginView.as_view(), name="login"),
    path("logout/", views.SilverScreenLogoutView.as_view(), name="logout"),
    path("register/", views.CustomerSignupView.as_view(), name="register"),
    path("movies/", views.MovieListView.as_view(), name="movies"),
    path("movies/<int:pk>/", views.MovieDetailView.as_view(), name="movie_detail"),
    path("booking/<int:showtime_id>/", views.BookingSeatsView.as_view(), name="booking"),
    path("booking/<int:showtime_id>/addons/", views.BookingAddonsView.as_view(), name="booking_addons"),
    path("booking/<int:showtime_id>/review/", views.BookingReviewView.as_view(), name="booking_review"),
    path("booking/orders/<str:number>/payment/", views.BookingPaymentView.as_view(), name="booking_payment"),
    path("orders/", views.OrderListView.as_view(), name="orders"),
    path("orders/table/", views.OrderTablePartialView.as_view(), name="orders_table"),
    path("orders/<str:number>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("orders/<str:number>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("orders/<str:number>/print/", views.OrderPrintView.as_view(), name="order_print"),
    path("payments/callback/", views.PaymentCallbackView.as_view(), name="payment_callback"),
    path("staff/pos/", views.CounterPOSView.as_view(), name="counter_pos"),
    path("staff/refunds/", views.RefundQueueView.as_view(), name="refund_queue"),
    path("staff/refunds/<int:pk>/complete/", views.RefundCompleteView.as_view(), name="refund_complete"),
    path("staff/orders/", views.OrderLookupView.as_view(), name="order_lookup"),
    path("scheduler/showtimes/", views.SchedulerShowTimeListView.as_view(), name="scheduler_showtimes"),
    path("scheduler/showtimes/new/", views.SchedulerShowTimeCreateView.as_view(), name="scheduler_showtime_new"),
    path("scheduler/showtimes/<int:pk>/disable/", views.SchedulerShowTimeDisableView.as_view(), name="scheduler_showtime_disable"),
    path("manager/", views.ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("manager/movies/", views.ManagerMovieListView.as_view(), name="manager_movies"),
    path("manager/movies/new/", views.ManagerMovieCreateView.as_view(), name="manager_movie_new"),
    path("manager/movies/<int:pk>/edit/", views.ManagerMovieUpdateView.as_view(), name="manager_movie_edit"),
    path("manager/movies/<int:pk>/toggle/", views.ManagerMovieToggleView.as_view(), name="manager_movie_toggle"),
    path("manager/products/", views.ManagerProductListView.as_view(), name="manager_products"),
    path("manager/products/new/", views.ManagerProductCreateView.as_view(), name="manager_product_new"),
    path("manager/products/<int:pk>/edit/", views.ManagerProductUpdateView.as_view(), name="manager_product_edit"),
    path("manager/products/<int:pk>/toggle/", views.ManagerProductToggleView.as_view(), name="manager_product_toggle"),
    path("manager/studios/", views.ManagerStudioListView.as_view(), name="manager_studios"),
    path("manager/studios/new/", views.ManagerStudioCreateView.as_view(), name="manager_studio_new"),
    path("manager/studios/<int:pk>/edit/", views.ManagerStudioUpdateView.as_view(), name="manager_studio_edit"),
    path("manager/studios/<int:pk>/toggle/", views.ManagerStudioToggleView.as_view(), name="manager_studio_toggle"),
]
