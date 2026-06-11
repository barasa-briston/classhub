import threading
from django.core.mail import send_mail
from django.conf import settings

def send_mail_background(subject, message, recipient_list, fail_silently=True, **kwargs):
    """
    Sends an email in a separate thread to avoid blocking the main request flow.
    """
    thread = threading.Thread(
        target=send_mail,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list),
        kwargs={'fail_silently': fail_silently, **kwargs}
    )
    thread.start()
