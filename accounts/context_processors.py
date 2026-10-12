from notifications.models import Notification


def unread_notifications_count(request):
    """
    Context processor providing the unread notifications count
    and latest 5 unread notifications for the currently logged-in user.
    """
    if request.user.is_authenticated:
        unread_qs = Notification.objects.filter(user=request.user, is_read=False)
        unread_count = unread_qs.count()
        recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
        return {
            'unread_count': unread_count,
            'header_notifications': recent_notifications,
        }
    return {
        'unread_count': 0,
        'header_notifications': [],
    }
