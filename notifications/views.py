import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Notification

logger = logging.getLogger(__name__)


@login_required
def notifications_view(request):
    """
    Renders user's notifications center with status filtering and pagination.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_read_view(request, pk):
    """Marks a single notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'success', 'notification_id': pk})

    messages.success(request, "Notification marked as read.")
    return redirect('notifications:notifications')


@login_required
@require_POST
def mark_all_read_view(request):
    """Marks all notifications for current user as read."""
    updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'success', 'updated_count': updated_count})

    messages.success(request, f"Marked {updated_count} notifications as read.")
    return redirect('notifications:notifications')


@login_required
def get_unread_count_view(request):
    """AJAX polling endpoint returning unread notification count."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})
