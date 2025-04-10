# VisAutoML/middleware.py
import requests
from django.http import HttpResponse, StreamingHttpResponse
import logging
import re

logger = logging.getLogger(__name__)

class DashboardProxyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Match /dashboard-proxy/<model_id>/<proxied_path>
        match = re.match(r'^api/dashboard/(?P<model_id>\d+)(?P<proxied_path>/.*)?$', path)
        if match:
            model_id = match.group("model_id")
            proxied_path = match.group("proxied_path") or "/"

            try:
                # Get the model to find its port
                from machine_learning.models import Model
                model = Model.objects.get(id=model_id)

                if not model.port:
                    return HttpResponse("Dashboard not started", status=404)

                # Build the target URL for the internal Dash server
                query_string = request.META.get('QUERY_STRING', '')
                if query_string:
                    target_url = f"http://localhost:{model.port}{proxied_path}?{query_string}"
                else:
                    target_url = f"http://localhost:{model.port}{proxied_path}"

                logger.info(f"Proxying request to: {target_url}")

                # Prepare the request to the internal server
                method = request.method.lower()
                request_kwargs = {
                    'headers': {
                        k: v for k, v in request.headers.items()
                        if k.lower() not in ['host', 'connection']
                    },
                    'stream': True,
                    'allow_redirects': False,
                }

                # Include data for write methods
                if method in ['post', 'put', 'patch']:
                    request_kwargs['data'] = request.body

                if request.GET:
                    request_kwargs['params'] = request.GET

                # Make the request to the Dash app
                dashboard_response = getattr(requests, method)(target_url, **request_kwargs)

                # Build the Django response
                response = StreamingHttpResponse(
                    streaming_content=dashboard_response.iter_content(chunk_size=8192),
                    content_type=dashboard_response.headers.get('Content-Type', 'text/html'),
                    status=dashboard_response.status_code,
                )

                # Copy headers
                excluded_headers = ['content-encoding', 'transfer-encoding', 'content-length', 'connection']
                for key, value in dashboard_response.headers.items():
                    if key.lower() not in excluded_headers:
                        response[key] = value

                return response

            except Exception as e:
                logger.error(f"Error proxying to dashboard: {str(e)}")
                return HttpResponse(f"Error proxying to dashboard: {str(e)}", status=500)

        # Not a dashboard request, proceed with the normal flow
        return self.get_response(request)
