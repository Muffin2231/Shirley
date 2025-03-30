from django.contrib import admin
from .models import Booking, Service, BookingSettings, Availability, OffDay
from django.utils import timezone
import pytz

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration', 'description')
    list_editable = ('duration',)
    search_fields = ('name',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('title', 'service', 'start_date_local', 'end_date_local', 'is_blocked')
    list_filter = ('is_blocked', 'service')
    date_hierarchy = 'start_date'
    fieldsets = (
        (None, {
            'fields': ('title', 'service', 'start_date', 'end_date', 'is_blocked'),
            'description': 'Customer bookings are auto-blocked. Check "Is blocked" for personal unavailable times.'
        }),
    )

    def start_date_local(self, obj):
        # Convert UTC to Mountain Time for display
        return timezone.localtime(obj.start_date, pytz.timezone('America/Denver')).strftime('%Y-%m-%d %H:%M:%S')
    start_date_local.short_description = 'Start Date (MT)'

    def end_date_local(self, obj):
        return timezone.localtime(obj.end_date, pytz.timezone('America/Denver')).strftime('%Y-%m-%d %H:%M:%S')
    end_date_local.short_description = 'End Date (MT)'

    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.is_blocked:
            return ['title', 'service']
        return []

@admin.register(BookingSettings)
class BookingSettingsAdmin(admin.ModelAdmin):
    list_display = ('max_booking_window_days', 'min_notice_hours', 'daily_booking_limit')

    def has_add_permission(self, request):
        return not BookingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week',)

@admin.register(OffDay)
class OffDayAdmin(admin.ModelAdmin):
    list_display = ('date', 'reason')
    list_filter = ('date',)
    date_hierarchy = 'date'