from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def add(value, arg):
    try:
        days = int(arg)
        date = datetime.strptime(value, '%Y-%m-%d')
        new_date = date + timedelta(days=days)
        return new_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return value