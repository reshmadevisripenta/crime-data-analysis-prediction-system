from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator for views that checks that the logged-in user is an administrator.
    Redirects to dashboard or raises PermissionDenied if unauthorized.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_admin():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Administrator privileges are required.")
        raise PermissionDenied("You do not have permission to view this resource.")
    return _wrapped_view


def analyst_required(view_func):
    """
    Decorator for views that checks that the logged-in user is an analyst or administrator.
    Redirects to dashboard or raises PermissionDenied if unauthorized.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_analyst():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Analyst privileges are required.")
        raise PermissionDenied("You do not have permission to view this resource.")
    return _wrapped_view
