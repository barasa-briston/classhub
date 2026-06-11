from django.utils.deprecation import MiddlewareMixin
from .signals import set_current_user

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)

    def process_response(self, request, response):
        set_current_user(None)
        return response
        
    def process_exception(self, request, exception):
        set_current_user(None)
