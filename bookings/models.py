from django.db import models

class Service(models.Model):
    name = models.CharField(max_length=200)
    duration = models.DurationField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    title = models.CharField(max_length=200)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.service} ({'Blocked' if self.is_blocked else 'Booked'})"

class BookingSettings(models.Model):
    max_booking_window_days = models.PositiveIntegerField(default=30, help_text="Max days ahead users can book")
    min_notice_hours = models.PositiveIntegerField(default=24, help_text="Min hours notice required for booking")
    daily_booking_limit = models.PositiveIntegerField(default=5, help_text="Max bookings per day")

    def __str__(self):
        return "Booking Settings"

    class Meta:
        verbose_name = "Booking Settings"
        verbose_name_plural = "Booking Settings"

class Availability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()  # e.g., 09:00
    end_time = models.TimeField()    # e.g., 17:00

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.start_time} - {self.end_time}"

class OffDay(models.Model):
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Off Day: {self.date} ({self.reason})"