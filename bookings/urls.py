from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('api/bookings/', views.get_bookings, name='get_bookings'),
    path('api/add-booking/', views.add_booking, name='add_booking'),
    path('api/availability/', views.get_availability, name='get_availability'),
    path('account/', views.account_view, name='account'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('edit/<int:booking_id>/', views.edit_booking, name='edit_booking'),
]