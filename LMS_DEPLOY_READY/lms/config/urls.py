# LMS URL Configuration
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from accounts.views import dashboard_redirect

urlpatterns = [
    path("", dashboard_redirect, name="home"),
    path("admin/", admin.site.urls),

    # Accounts (Main Dashboards)
    path("", include("accounts.urls")),
    
    path('approvals/', include('approvals.urls')),
    path('communications/', include('communications.urls')),
    path('audit/', include('audit.urls')),
    
    # API endpoints for assignments and submissions
    path("api/assignments/", include("assignments.urls")),
    path("api/submissions/", include("submissions.urls")),

    # Sub-app specific actions (prefixed to avoid clashes)
    path("assignments-old/", include("assignments.web_urls")),
    path("submissions-old/", include("submissions.web_urls")),
    path("approvals-old/", include("approvals.web_urls")),
]

handler404 = 'accounts.views.custom_404'
handler500 = 'accounts.views.custom_500'

from django.views.decorators.clickjacking import xframe_options_exempt

# Serve media files (student submissions, etc.)
# Using serve view here ensures files are accessible even when DEBUG=False 
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', xframe_options_exempt(serve), {'document_root': settings.MEDIA_ROOT}),
]
