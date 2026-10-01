from django.urls import path

from .views import (
    DeliveryLocationListView,
    ShippingAddressDetailView,
    ShippingAddressListCreateView,
)

urlpatterns = [
    path("delivery-locations/", DeliveryLocationListView.as_view(), name="delivery-location-list",),
    path("shipping-addresses/", ShippingAddressListCreateView.as_view(), name="shipping-address-list",),
    path("shipping-addresses/<int:pk>/", ShippingAddressDetailView.as_view(), name="shipping-address-detail",),
]
