from django.urls import path

from .views import SliderItemListView

urlpatterns = [
    path("slider/", SliderItemListView.as_view(), name="slider-list"),
]
