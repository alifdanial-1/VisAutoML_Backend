# VisAutoML/middleware.py
import requests
from django.http import HttpResponse, StreamingHttpResponse
import logging

logger = logging.getLogger(__name__)

class DashboardProxyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Check if the request is for a dashboard
        if path.startswith('/dashboard-proxy/'):
            try:
                # Extract the model_id from the URL
                parts = path.split('/')
                if len(parts) < 3:
                    return HttpResponse("Invalid dashboard URL", status=400)
                
                model_id = parts[2]
                
                # Get the model to find its port
                from machine_learning.models import Model
                model = Model.objects.get(id=model_id)
                
                if not model.port:
                    return HttpResponse("Dashboard not started", status=404)
                
                # Build the path to forward to the dashboard
                remaining_path = '/'.join(parts[3:])
                query_string = request.META.get('QUERY_STRING', '')
                if query_string:
                    target_url = f"http://localhost:{model.port}/{remaining_path}?{query_string}"
                else:
                    target_url = f"http://localhost:{model.port}/{remaining_path}"
                
                logger.info(f"Proxying request to: {target_url}")
                
                # Forward the request to the dashboard
                method = request.method.lower()
                request_kwargs = {
                    'headers': {k: v for k, v in request.headers.items() 
                               if k.lower() not in ['host', 'connection']},
                    'stream': True,
                    'allow_redirects': False,
                }
                
                # Add data if it's a POST, PUT, etc.
                if method in ['post', 'put', 'patch']:
                    request_kwargs['data'] = request.body
                
                # Add query params
                if request.GET:
                    request_kwargs['params'] = request.GET
                
                # Make the request to the dashboard
                dashboard_response = getattr(requests, method)(target_url, **request_kwargs)
                
                # Create Django response from dashboard response
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
        
        # Not a dashboard request, continue with regular processing
        return self.get_response(request)