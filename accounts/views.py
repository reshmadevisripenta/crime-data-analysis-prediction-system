import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.urls import reverse_lazy
from .forms import LoginForm, RegisterForm, ProfileForm, SettingsForm
from notifications.models import Notification

logger = logging.getLogger(__name__)


def login_view(request):
    """
    User login view. Redirects already authenticated users to the dashboard.
    Supports remember me session duration persistence.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            remember_me = form.cleaned_data.get('remember_me')
            if not remember_me:
                # Session expires when user closes browser
                request.session.set_expiry(0)
            else:
                # 30 days session
                request.session.set_expiry(30 * 86400)

            logger.info(f"User {user.username} logged in successfully.")
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, "Invalid credentials. Please verify your username and password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    """
    New user registration view. Redirects authenticated users to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info(f"New user registered: {user.username} ({user.email})")
            
            # Send initial welcome notification
            Notification.create_notification(
                user=user,
                title="Welcome to Crime Data Analysis & Prediction System",
                message="Your account has been successfully created. Explore crime analytics and prediction dashboards.",
                notif_type="success",
                category="system",
                action_url="/dashboard/"
            )

            messages.success(request, "Your account has been created successfully! You can now log in.")
            return redirect('accounts:login')
        else:
            messages.error(request, "Registration failed. Please correct the highlighted errors.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def logout_view(request):
    """Logs out the user via POST request only for security."""
    username = request.user.username if request.user.is_authenticated else "Anonymous"
    logout(request)
    logger.info(f"User {username} logged out.")
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    Profile management view. Displays profile on GET, saves updates on POST.
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            logger.info(f"User {request.user.username} updated profile.")
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors in the profile form.")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'user': request.user,
    })


@login_required
def settings_view(request):
    """
    User settings and preferences view.
    """
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            logger.info(f"User {request.user.username} updated settings.")
            messages.success(request, "Your settings have been saved successfully.")
            return redirect('accounts:settings')
        else:
            messages.error(request, "Failed to update settings. Please check the form.")
    else:
        form = SettingsForm(instance=request.user)

    return render(request, 'accounts/settings.html', {
        'form': form,
        'user': request.user,
    })


class CustomPasswordResetView(PasswordResetView):
    """Password reset request view."""
    template_name = 'accounts/forgot_password.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
