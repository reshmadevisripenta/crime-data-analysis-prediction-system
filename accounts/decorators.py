from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator for views that checks that the logged-in user is an administrator.
    Redirects to dashboard with a friendly message if the user lacks admin privileges.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_admin():
            return view_func(request, *args, **kwargs)
        messages.error(
            request,
            "⛔ Access Denied: This page requires Administrator privileges. "
            "Please contact your system administrator if you believe this is an error."
        )
        return redirect('dashboard:dashboard')
    return _wrapped_view


def analyst_required(view_func):
    """
    Decorator for views that checks that the logged-in user is an analyst or administrator.
    Redirects to dashboard with a friendly message if the user lacks analyst privileges.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_analyst():
            return view_func(request, *args, **kwargs)
        messages.error(
            request,
            "⛔ Access Denied: This page requires Analyst or Administrator privileges. "
            "Your current role is '{}'. Please contact an administrator to upgrade your access.".format(
                request.user.get_role_display()
            )
        )
        return redirect('dashboard:dashboard')
    return _wrapped_view
