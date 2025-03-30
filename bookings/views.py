from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Booking, Service, BookingSettings, Availability, OffDay
import json
from django.db.models import Q, Count
from django.urls import reverse
from datetime import datetime, timedelta, time
import pytz

@login_required
def calendar_view(request):
    services = Service.objects.all()
    services_data = [
        {'id': service.id, 'name': service.name, 'duration': str(service.duration), 'description': service.description}
        for service in services
    ]
    today = datetime.now().date()
    settings = BookingSettings.objects.first()
    settings_data = {
        'max_booking_window_days': settings.max_booking_window_days,
        'min_notice_hours': settings.min_notice_hours,
        'daily_booking_limit': settings.daily_booking_limit
    } if settings else {
        'max_booking_window_days': 30,
        'min_notice_hours': 24,
        'daily_booking_limit': 5
    }

    # Get availability and off days
    availability = Availability.objects.all()
    off_days = OffDay.objects.all()
    off_days_dates = [off_day.date for off_day in off_days]

    # Calculate available dates
    bookings = Booking.objects.all()
    available_dates = []
    max_date = today + timedelta(days=settings_data['max_booking_window_days'])
    current_date = today
    now = datetime.now(pytz.UTC)

    while current_date <= max_date:
        # Skip off days
        if current_date in off_days_dates:
            current_date += timedelta(days=1)
            continue

        # Check if the date is within the minimum notice period
        day_start = datetime.combine(current_date, time.min, tzinfo=pytz.UTC)
        if day_start < now + timedelta(hours=settings_data['min_notice_hours']):
            current_date += timedelta(days=1)
            continue

        # Check daily booking limit
        day_end = day_start + timedelta(days=1)
        daily_bookings = Booking.objects.filter(start_date__gte=day_start, start_date__lt=day_end).count()
        if daily_bookings >= settings_data['daily_booking_limit']:
            current_date += timedelta(days=1)
            continue

        # Check if the day has availability
        day_of_week = current_date.weekday()
        print(f"Date: {current_date}, Day of Week: {day_of_week}")  # Debug log
        day_availability = availability.filter(day_of_week=day_of_week).first()
        if not day_availability:
            current_date += timedelta(days=1)
            continue

        # Check for available slots within the day's availability
        has_available_slot = False
        for service in services:
            duration_ms = service.duration.total_seconds() * 1000
            start_time = datetime.combine(current_date, day_availability.start_time, tzinfo=pytz.timezone('America/Denver'))
            end_time = datetime.combine(current_date, day_availability.end_time, tzinfo=pytz.timezone('America/Denver'))
            start_time = start_time.astimezone(pytz.UTC)
            end_time = end_time.astimezone(pytz.UTC)
            slot_duration = 15 * 60 * 1000  # 15-minute increments

            while start_time + timedelta(milliseconds=duration_ms) <= end_time:
                slot_end = start_time + timedelta(milliseconds=duration_ms)
                if start_time < now + timedelta(hours=settings_data['min_notice_hours']):
                    start_time += timedelta(minutes=15)
                    continue
                overlap = Booking.objects.filter(
                    Q(start_date__lt=slot_end) & Q(end_date__gt=start_time)
                ).exists()
                if not overlap:
                    has_available_slot = True
                    break
                start_time += timedelta(minutes=15)

            if has_available_slot:
                break

        if has_available_slot:
            available_dates.append(current_date.strftime('%Y-%m-%d'))

        current_date += timedelta(days=1)

    print("Available Dates:", available_dates)  # Debug log
    return render(request, 'calendar.html', {
        'services': services_data,
        'today': today,
        'settings': settings_data,
        'available_dates': available_dates
    })

@login_required
def get_bookings(request):
    bookings = Booking.objects.all()
    events = []
    # Define colors for different services (example mapping)
    service_colors = {
        'Swedish Massage': '#1a73e8',  # Blue
        'Deep Tissue Massage': '#34a853',  # Green
        'Test': '#fbbc05',  # Yellow
    }
    for booking in bookings:
        service_name = booking.service.name
        if booking.title == request.user.username and not booking.is_blocked:
            title = f"{booking.title} - {service_name} ({booking.service.duration})"
            color = service_colors.get(service_name, '#1a73e8')  # Default to blue if service not in map
            description = booking.service.description
        else:
            title = "Unavailable"
            color = 'red'
            description = "This time slot is booked or blocked."
        events.append({
            'id': booking.id,
            'title': title,
            'start': booking.start_date.isoformat(),
            'end': booking.end_date.isoformat(),
            'color': color,
            'description': description,  # For tooltips
        })
    return JsonResponse(events, safe=False)

@csrf_exempt
@login_required
def add_booking(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        start = data['start']
        service_id = data['service_id']
        title = request.user.username

        service = Service.objects.get(id=service_id)
        start_dt = datetime.fromisoformat(start.rstrip('Z')).replace(tzinfo=pytz.UTC)
        end_dt = start_dt + service.duration
        settings = BookingSettings.objects.first()
        now = datetime.now(pytz.UTC)

        # Check minimum notice
        if start_dt < now + timedelta(hours=settings.min_notice_hours):
            return JsonResponse({'status': 'error', 'message': f'Booking requires at least {settings.min_notice_hours} hours notice'}, status=400)

        # Check maximum booking window
        if start_dt.date() > now.date() + timedelta(days=settings.max_booking_window_days):
            return JsonResponse({'status': 'error', 'message': f'Booking cannot be more than {settings.max_booking_window_days} days ahead'}, status=400)

        # Check daily booking limit
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        daily_bookings = Booking.objects.filter(start_date__gte=day_start, start_date__lt=day_end).count()
        if daily_bookings >= settings.daily_booking_limit:
            return JsonResponse({'status': 'error', 'message': f'Daily booking limit of {settings.daily_booking_limit} reached'}, status=400)

        # Check off days
        off_days = OffDay.objects.all()
        off_days_dates = [off_day.date for off_day in off_days]
        if start_dt.date() in off_days_dates:
            return JsonResponse({'status': 'error', 'message': 'This date is marked as an off day'}, status=400)

        # Check availability
        day_of_week = start_dt.weekday()
        availability = Availability.objects.filter(day_of_week=day_of_week).first()
        if not availability:
            return JsonResponse({'status': 'error', 'message': 'Specialist is not available on this day'}, status=400)

        day_start = start_dt.replace(hour=availability.start_time.hour, minute=availability.start_time.minute, second=0, microsecond=0)
        day_end = start_dt.replace(hour=availability.end_time.hour, minute=availability.end_time.minute, second=0, microsecond=0)
        if start_dt < day_start or end_dt > day_end:
            return JsonResponse({'status': 'error', 'message': 'Time slot is outside specialist availability'}, status=400)

        # Check for overlaps
        overlap = Booking.objects.filter(
            Q(start_date__lt=end_dt) & Q(end_date__gt=start_dt)
        ).exists()

        if overlap:
            return JsonResponse({'status': 'error', 'message': 'Time slot is already booked or blocked'}, status=400)

        booking = Booking(
            title=title,
            service=service,
            start_date=start_dt,
            end_date=end_dt,
            is_blocked=False
        )
        booking.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def account_view(request):
    user_bookings = Booking.objects.filter(title=request.user.username, is_blocked=False)
    bookings_data = [
        {
            'id': booking.id,
            'start_date': booking.start_date.isoformat(),
            'service': {'name': booking.service.name}
        }
        for booking in user_bookings
    ]
    services = Service.objects.all()
    services_data = [
        {'id': service.id, 'name': service.name, 'duration': str(service.duration), 'description': service.description}
        for service in services
    ]
    today = datetime.now().date()
    settings = BookingSettings.objects.first()
    settings_data = {
        'max_booking_window_days': settings.max_booking_window_days,
        'min_notice_hours': settings.min_notice_hours,
        'daily_booking_limit': settings.daily_booking_limit
    } if settings else {
        'max_booking_window_days': 30,
        'min_notice_hours': 24,
        'daily_booking_limit': 5
    }

    # Get availability and off days
    availability = Availability.objects.all()
    off_days = OffDay.objects.all()
    off_days_dates = [off_day.date for off_day in off_days]

    # Calculate available dates
    bookings = Booking.objects.all()
    available_dates = []
    max_date = today + timedelta(days=settings_data['max_booking_window_days'])
    current_date = today
    now = datetime.now(pytz.UTC)

    while current_date <= max_date:
        if current_date in off_days_dates:
            current_date += timedelta(days=1)
            continue

        day_start = datetime.combine(current_date, datetime.min.time(), tzinfo=pytz.UTC)
        if day_start < now + timedelta(hours=settings_data['min_notice_hours']):
            current_date += timedelta(days=1)
            continue

        day_end = day_start + timedelta(days=1)
        daily_bookings = Booking.objects.filter(start_date__gte=day_start, start_date__lt=day_end).exclude(id__in=[b.id for b in user_bookings]).count()
        if daily_bookings >= settings_data['daily_booking_limit']:
            current_date += timedelta(days=1)
            continue

        day_of_week = current_date.weekday()
        print(f"Date: {current_date}, Day of Week: {day_of_week}")  # Debug log
        day_availability = availability.filter(day_of_week=day_of_week).first()
        if not day_availability:
            current_date += timedelta(days=1)
            continue

        has_available_slot = False
        for service in services:
            duration_ms = service.duration.total_seconds() * 1000
            start_time = datetime.combine(current_date, day_availability.start_time, tzinfo=pytz.timezone('America/Denver'))
            end_time = datetime.combine(current_date, day_availability.end_time, tzinfo=pytz.timezone('America/Denver'))
            start_time = start_time.astimezone(pytz.UTC)
            end_time = end_time.astimezone(pytz.UTC)
            slot_duration = 15 * 60 * 1000

            while start_time + timedelta(milliseconds=duration_ms) <= end_time:
                slot_end = start_time + timedelta(milliseconds=duration_ms)
                if start_time < now + timedelta(hours=settings_data['min_notice_hours']):
                    start_time += timedelta(minutes=15)
                    continue
                overlap = Booking.objects.filter(
                    Q(start_date__lt=slot_end) & Q(end_date__gt=start_time)
                ).exclude(id__in=[b.id for b in user_bookings]).exists()
                if not overlap:
                    has_available_slot = True
                    break
                start_time += timedelta(minutes=15)

            if has_available_slot:
                break

        if has_available_slot:
            available_dates.append(current_date.strftime('%Y-%m-%d'))

        current_date += timedelta(days=1)

    print("Available Dates:", available_dates)  # Debug log
    return render(request, 'account.html', {
        'bookings': user_bookings,
        'bookings_data': bookings_data,
        'services': services_data,
        'today': today,
        'settings': settings_data,
        'available_dates': available_dates
    })

@login_required
def cancel_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id, title=request.user.username, is_blocked=False)
        booking.delete()
    except Booking.DoesNotExist:
        pass
    return HttpResponseRedirect(reverse('account'))

@csrf_exempt
@login_required
def edit_booking(request, booking_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        start = data['start']
        booking = Booking.objects.get(id=booking_id, title=request.user.username, is_blocked=False)
        service = booking.service
        start_dt = datetime.fromisoformat(start.rstrip('Z')).replace(tzinfo=pytz.UTC)
        end_dt = start_dt + service.duration
        settings = BookingSettings.objects.first()
        now = datetime.now(pytz.UTC)

        # Check minimum notice
        if start_dt < now + timedelta(hours=settings.min_notice_hours):
            return JsonResponse({'status': 'error', 'message': f'Booking requires at least {settings.min_notice_hours} hours notice'}, status=400)

        # Check maximum booking window
        if start_dt.date() > now.date() + timedelta(days=settings.max_booking_window_days):
            return JsonResponse({'status': 'error', 'message': f'Booking cannot be more than {settings.max_booking_window_days} days ahead'}, status=400)

        # Check daily booking limit (excluding this booking’s original day)
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        daily_bookings = Booking.objects.filter(start_date__gte=day_start, start_date__lt=day_end).exclude(id=booking_id).count()
        if daily_bookings >= settings.daily_booking_limit:
            return JsonResponse({'status': 'error', 'message': f'Daily booking limit of {settings.daily_booking_limit} reached'}, status=400)

        # Check off days
        off_days = OffDay.objects.all()
        off_days_dates = [off_day.date for off_day in off_days]
        if start_dt.date() in off_days_dates:
            return JsonResponse({'status': 'error', 'message': 'This date is marked as an off day'}, status=400)

        # Check availability
        day_of_week = start_dt.weekday()
        availability = Availability.objects.filter(day_of_week=day_of_week).first()
        if not availability:
            return JsonResponse({'status': 'error', 'message': 'Specialist is not available on this day'}, status=400)

        day_start = start_dt.replace(hour=availability.start_time.hour, minute=availability.start_time.minute, second=0, microsecond=0)
        day_end = start_dt.replace(hour=availability.end_time.hour, minute=availability.end_time.minute, second=0, microsecond=0)
        if start_dt < day_start or end_dt > day_end:
            return JsonResponse({'status': 'error', 'message': 'Time slot is outside specialist availability'}, status=400)

        # Check for overlaps
        overlap = Booking.objects.filter(
            Q(start_date__lt=end_dt) & Q(end_date__gt=start_dt)
        ).exclude(id=booking_id).exists()

        if overlap:
            return JsonResponse({'status': 'error', 'message': 'New time slot is already booked or blocked'}, status=400)

        booking.start_date = start_dt
        booking.end_date = end_dt
        booking.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def get_availability(request):
    day_of_week = request.GET.get('day_of_week')
    availability = Availability.objects.filter(day_of_week=day_of_week).first()
    if availability:
        return JsonResponse({
            'start_time': availability.start_time.strftime('%H:%M:%S'),
            'end_time': availability.end_time.strftime('%H:%M:%S')
        })
    return JsonResponse({}, status=404)