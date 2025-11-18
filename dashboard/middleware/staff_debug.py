import sys
from django.conf import settings
from django.views.debug import technical_500_response

class StaffDebugMiddleware:
    """
    Show the full technical 500 error page only to authenticated staff users.
    """
    def __init__(self, get_response):
        self.get_response = get_response  # <-- fix the typo

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception:
            # Only show technical 500 to staff users
            user = getattr(request, "user", None)
            if user and user.is_authenticated and user.is_staff:
                # Provide the exc_info for technical_500_response
                return technical_500_response(request, *sys.exc_info())
            # For everyone else, re-raise the exception
            raise
