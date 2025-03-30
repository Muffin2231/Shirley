from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm  # Import the custom form
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('calendar')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)  # Use custom form
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('calendar')
        else:
            messages.error(request, 'Registration failed. Check your input.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})