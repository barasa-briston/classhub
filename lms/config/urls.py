from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import dashboard_redirect

urlpatterns = [
    path("", dashboard_redirect, name="home"),
    path("admin/", admin.site.urls),

    # Accounts (Main Dashboards)
    path("", include("accounts.urls")),

    # Sub-app specific actions (prefixed to avoid clashes)
    path("assignments-old/", include("assignments.web_urls")),
    path("submissions-old/", include("submissions.web_urls")),
    path("approvals-old/", include("approvals.web_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
