from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path("", views.index),
    path("home/", views.index),
    
    # API endpoints
    path("api/", views.ModelViewSet.as_view({"get": "list", "post": "create"})),
    path("api/flask/", views.FlaskModelViewSet.as_view({"post": "create"})),
    path("api/table/", views.FlaskModelViewSet.as_view({"get": "list"})),
    path("api/<pk>/", views.ModelViewSet.as_view({"delete": "destroy"})),
    path("api/description/<pk>/", views.ModelDescriptionViewSet.as_view({"patch": "update"})),
    path("api/dashboard/<pk>/", views.ModelViewSet.as_view({"post": "open"})),

    # Dashboard UI pages
    # path("dashboards/", views.dashboard_index, name="dashboard_index"),
    path("dashboards/", views.dashboard_view, name="dashboard_view"),
    path("dashboards/<int:model_id>/", views.model_dashboard, name="model_dashboard"),

    # Optional: start/view/status if still used for launching dashboards
    path("dashboard/start/<pk>/", views.dashboard, name="start_dashboard"),
    path("dashboard/view/<pk>/", views.dashboard_view, name="view_dashboard"),
    path("dashboard/status/<pk>/", views.dashboard_status, name="dashboard_status"),

    path("test-media/", TemplateView.as_view(template_name='machine_learning/test_media.html')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
