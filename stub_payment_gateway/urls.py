from django.urls import path

from . import views

app_name = "stub_gateway"

urlpatterns = [
    path("", views.GatewayPaymentListView.as_view(), name="payments"),
    path("issue-payment/", views.IssuePaymentView.as_view(), name="issue_payment"),
    path("pay/<str:gateway_payment_id>/", views.GatewayPaymentView.as_view(), name="pay"),
    path("pay/<str:gateway_payment_id>/success/", views.GatewaySuccessView.as_view(), name="success"),
    path("pay/<str:gateway_payment_id>/expire/", views.GatewayExpireView.as_view(), name="expire"),
]
