import logging
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to log key actions (POST requests) into AuditLog:
    - User Login / Logout
    - Dataset Uploads
    - Analysis runs, predictions, and report generation
    Only logs successful POST requests (status code 200 or 302).
    """

    def process_response(self, request, response):
        if request.method != 'POST':
            return response

        # Only log successful POST requests (status 200 or 302)
        if response.status_code not in (200, 302):
            return response

        path = request.path

        action = None
        resource_type = ''
        details = {}

        if path.startswith('/accounts/login/'):
            action = 'login'
            resource_type = 'Authentication'
            details = {'path': path}
        elif path.startswith('/accounts/logout/'):
            action = 'logout'
            resource_type = 'Authentication'
            details = {'path': path}
        elif path.startswith('/crime-data/upload/'):
            action = 'upload'
            resource_type = 'CrimeDataset'
            details = {'path': path}
        elif '/analysis/' in path:
            action = 'analysis'
            resource_type = 'DataAnalysis'
            details = {'path': path}
        elif '/prediction/' in path or '/model-training/' in path:
            if '/model-training/' in path:
                action = 'training'
                resource_type = 'ModelTraining'
            else:
                action = 'prediction'
                resource_type = 'CrimePrediction'
            details = {'path': path}
        elif '/reports/' in path:
            action = 'report'
            resource_type = 'Report'
            details = {'path': path}

        if action:
            try:
                user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
                ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
                if ip_address:
                    ip_address = ip_address.split(',')[0].strip()
                else:
                    ip_address = request.META.get('REMOTE_ADDR')

                # Handle localhost ipv6 format if needed or length constraints
                if ip_address and len(ip_address) > 45:
                    ip_address = ip_address[:45]

                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

                AuditLog.objects.create(
                    user=user,
                    action=action,
                    resource_type=resource_type,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                logger.warning(f"Failed to record audit log: {e}")

        return response
