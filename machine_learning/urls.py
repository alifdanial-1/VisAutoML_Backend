# from django.contrib import admin
# from django.urls import path, include, re_path
# from django.conf import settings
# from django.conf.urls.static import static
# from django.views.generic import TemplateView
# from django.views.static import serve
# from . import views
# import os

# urlpatterns = [
#     path("", views.index),
#     path("home/", views.index),
#     path("api/", views.ModelViewSet.as_view({"get": "list", "post": "create"})),
#     path("api/flask/", views.FlaskModelViewSet.as_view({"post": "create"})),
#     path("api/table/", views.FlaskModelViewSet.as_view({"get": "list"})),
#     path("api/<pk>/", views.ModelViewSet.as_view({"delete": "destroy"})),
#     path("api/description/<pk>/",
#          views.ModelDescriptionViewSet.as_view({"patch": "update"})),
#     path("api/dashboard/<pk>/", views.ModelViewSet.as_view({"post":"open"})),
#     path("test-media/", TemplateView.as_view(template_name='machine_learning/test_media.html')),
# ]

# # Serve static files during development
# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
from . import views
import os

urlpatterns = [
    path("", views.index),
    path("home/", views.index),
    path("api/", views.ModelViewSet.as_view({"get": "list", "post": "create"})),
    path("api/flask/", views.FlaskModelViewSet.as_view({"post": "create"})),
    path("api/table/", views.FlaskModelViewSet.as_view({"get": "list"})),
    path("api/<pk>/", views.ModelViewSet.as_view({"delete": "destroy"})),
    path("api/description/<pk>/",
         views.ModelDescriptionViewSet.as_view({"patch": "update"})),
    path("api/dashboard/<pk>/", views.ModelViewSet.as_view({"post":"open"})),
    
    # New dashboard-specific routes
    path("dashboard/start/<pk>/", views.dashboard, name="start_dashboard"),
    path("dashboard/view/<pk>/", views.dashboard_view, name="view_dashboard"),
    path("dashboard/status/<pk>/", views.dashboard_status, name="dashboard_status"),
    
    path("test-media/", TemplateView.as_view(template_name='machine_learning/test_media.html')),
]

# Special route for dashboard proxy - this needs to capture all paths under dashboard-proxy
# This will be handled by the middleware
re_path(r'^dashboard-proxy/(?P<model_id>\d+)/(?P<path>.*)$', views.dashboard_proxy, name='dashboard_proxy'),

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)