# Generated by Django 5.1.7 on 2025-03-30 03:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_booking_window_days', models.PositiveIntegerField(default=30, help_text='Max days ahead users can book')),
                ('min_notice_hours', models.PositiveIntegerField(default=24, help_text='Min hours notice required for booking')),
                ('daily_booking_limit', models.PositiveIntegerField(default=5, help_text='Max bookings per day')),
            ],
            options={
                'verbose_name': 'Booking Settings',
                'verbose_name_plural': 'Booking Settings',
            },
        ),
    ]
