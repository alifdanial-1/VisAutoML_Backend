from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

# Define URL patterns
urlpatterns = [
    # Admin URL
    path('admin/', admin.site.urls),
    
    # App URLs
    path("", include("machine_learning.urls")),
    
    # Serve media files
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT
    }),
    
    # Serve static files
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),
    
    # Serve image files directly from img directory
    re_path(r'^img/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'img')
    }),
    
    # Serve datasets files
    re_path(r'^datasets/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.MEDIA_ROOT, 'datasets')
    }),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
