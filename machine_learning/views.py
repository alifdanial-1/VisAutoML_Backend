import os
import traceback
import threading
import socket
from contextlib import closing

import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, status
from rest_framework.response import Response

from machine_learning.dashboard import runModel
from .serializers import ModelSerializer, ModelDescriptionSerializer
from .models import Model, ModelDescription
from .review import get_review

# Constants
BASE_PORT = 8050
MAX_DASHBOARDS = 30

# Logging setup
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('model_operations.log'), logging.StreamHandler()]
)

# === UTILS ===

def is_port_available(port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(('localhost', port)) != 0

def get_assigned_port(model_instance):
    if model_instance.port and is_port_available(model_instance.port):
        return model_instance.port

    used_ports = Model.objects.exclude(port__isnull=True).values_list('port', flat=True)
    for port in range(BASE_PORT, BASE_PORT + MAX_DASHBOARDS):
        if port not in used_ports and is_port_available(port):
            model_instance.port = port
            model_instance.save()
            return port

    raise Exception("No available ports to assign!")

def launch_dashboard_async(model_id, port):
    try:
        runModel(str(model_id), port)
    except Exception as e:
        logger.error(f"Failed to launch dashboard for model {model_id} on port {port}: {str(e)}")

# === VIEWS ===

def index(request):
    return render(request, "machine_learning/index.html")

def dashboard_view(request, pk):
    return render(request, "machine_learning/dashboard_view.html", {"model_id": pk})

def dashboard_status(request, pk):
    try:
        model_instance = Model.objects.get(id=pk)

        if not model_instance.port:
            return JsonResponse({"status": "not_started"})

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            in_use = sock.connect_ex(('localhost', model_instance.port)) == 0

        return JsonResponse({
            "status": "running" if in_use else "stopped",
            "port": model_instance.port,
            "dashboard_url": f"/dashboard-proxy/{pk}/" if in_use else None
        })
    except Exception as e:
        logger.error(f"Error checking dashboard status: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def dashboard_proxy(request, model_id, path):
    return HttpResponse("Dashboard proxy error. Middleware not working properly.", status=500)

def dashboard(request, pk):
    try:
        model_instance = Model.objects.get(id=pk)
        port = get_assigned_port(model_instance)

        logger.info(f"Launching dashboard for model {pk} on port {port}")
        threading.Thread(target=launch_dashboard_async, args=(pk, port), daemon=True).start()

        return JsonResponse({
            "response": "Success",
            "dashboard_url": f"/dashboard-proxy/{pk}/",
            "port": port
        })

    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}")
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

# === VIEWSETS ===

class ModelViewSet(viewsets.ViewSet):

    def list(self, request):
        models = Model.objects.all().order_by('-id')
        serializer = ModelSerializer(models, many=True)
        return Response(serializer.data)

    def create(self, request):
        try:
            serializer = ModelSerializer(data=request.data)
            if serializer.is_valid():
                model_instance = serializer.save()
                result = get_review(model_instance.data_set.path)
                description = ModelDescription.objects.create(model=model_instance, description={})
                description_serializer = ModelDescriptionSerializer(description)

                port = get_assigned_port(model_instance)
                model_instance.port = port
                model_instance.save()

                return Response({
                    "response": result,
                    "model": serializer.data,
                    "description": description_serializer.data,
                    "port": port
                })

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating model: {str(e)}")
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

    def destroy(self, request, pk):
        Model.objects.get(id=pk).delete()
        models = Model.objects.all().order_by('-id')
        serializer = ModelSerializer(models, many=True)
        return Response(serializer.data)

    def open(self, request, pk):
        try:
            model_instance = Model.objects.get(id=pk)
            port = get_assigned_port(model_instance)

            yaml_file = f"{pk}.yaml"
            if not os.path.exists(yaml_file):
                return Response({"error": f"Configuration file {yaml_file} not found"}, status=404)

            os.system(f"npx kill-port {port}")
            os.system(f'explainerdashboard run {yaml_file} --no-browser --port={port}')
            return Response({"response": "Success", "port": port})
        except Exception as e:
            logger.error(f"Error opening dashboard: {str(e)}")
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

class ModelDescriptionViewSet(viewsets.ViewSet):

    def update(self, request, pk):
        description = ModelDescription.objects.get(id=pk)
        serializer = ModelDescriptionSerializer(description, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FlaskModelViewSet(viewsets.ViewSet):

    def list(self, request):
        models = Model.objects.all().order_by('-id')
        for model in models:
            model.model_type = "Regression" if model.model_type == "RG" else "Classification"
        serializer = ModelSerializer(models, many=True)
        return Response(serializer.data)

    def create(self, request):
        try:
            model_obj = Model.objects.get(id=request.data["model"])
            description_obj = ModelDescription.objects.get(id=request.data["description"])
            model_id = request.data["model"]

            model_obj.algorithm_name = request.data.get("algo", "auto")
            model_obj.save()

            # Assign port
            port = get_assigned_port(model_obj)
            if not model_obj.port:
                model_obj.port = port
                model_obj.save()

            # Start in thread
            t = threading.Thread(target=self.run, args=(
                model_obj.data_set,
                request.data.get("projectTitle", "Project"),
                request.data.get("auto", 1),
                request.data.get("id_column", "null"),
                request.data.get("prediction_column", "null"),
                request.data.get("not_to_use_columns", ["null"]),
                description_obj.description,
                request.data.get("algo", "auto"),
                model_id,
                model_obj.model_type,
                request.data.get("unit", "null"),
                request.data.get("label0", "null"),
                request.data.get("label1", "null"),
                request.data.get("split", "0.2"),
                port
            ))
            t.start()
            t.join()

            return Response(data={"message": "success", "port": port}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in model creation: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"error": str(e)}, status=500)

    def run(self, train_csv_path, project_title, auto, id_column, predict, drop, descriptions,
            algo, model_id, model_type, unit, label0, label1, split, port):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            os.chdir(base_dir)
            os.system(f"npx kill-port {port}")

            if model_type == 'CL':
                command = (
                    f'python machine_learning/classifier_custom_explainer.py '
                    f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
                    f'"{descriptions}" {algo} {model_id} "{label0}" "{label1}" "{split}" --port {port}'
                )
            else:
                command = (
                    f'python machine_learning/regression_custom_explainer.py '
                    f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
                    f'"{descriptions}" {algo} {model_id} "{unit}" "{split}" --port {port}'
                )

            logger.info(f"Executing command: {command}")
            result = os.system(command)
            logger.info(f"Command execution completed with status: {result}")

        except Exception as e:
            logger.error(f"Error running model {model_id}: {str(e)}")
            logger.error(traceback.format_exc())


# import os
# import traceback
# import threading
# from multiprocessing import Process
# import pandas as pd
# import socket
# from contextlib import closing

# from rest_framework import viewsets, status, decorators, views
# from rest_framework.response import Response
# from rest_framework.decorators import api_view
# from django.shortcuts import render
# from django.http import JsonResponse

# from machine_learning.dashboard import runModel

# from .serializers import ModelSerializer, ModelDescriptionSerializer
# from .models import Model, ModelDescription  # Make sure Model has a 'port' field (IntegerField, null=True, blank=True)
# from .review import get_review
# from .regression_custom_explainer import finishing
# # from .dashboard import runModel as original_runModel  # We now override runModel below
# # utils.py

# # Base port and maximum dashboards to run concurrently
# BASE_PORT = 8050
# MAX_DASHBOARDS = 30

# import logging

# # Configure logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('model_operations.log'),
#         logging.StreamHandler()
#     ]
# )

# def dashboard_view(request, pk):
#     """
#     Renders a template that loads the dashboard in an iframe
#     """
#     return render(request, "machine_learning/dashboard_view.html", {"model_id": pk})

# def dashboard_status(request, pk):
#     """
#     Check if dashboard is running
#     """
#     try:
#         model_instance = Model.objects.get(id=pk)
        
#         if not model_instance.port:
#             return JsonResponse({"status": "not_started"})
        
#         # Check if port is in use
#         with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
#             in_use = sock.connect_ex(('localhost', model_instance.port)) == 0
        
#         return JsonResponse({
#             "status": "running" if in_use else "stopped",
#             "port": model_instance.port,
#             "dashboard_url": f"/dashboard-proxy/{pk}/" if in_use else None
#         })
        
#     except Exception as e:
#         logger.error(f"Error checking dashboard status: {str(e)}")
#         return JsonResponse({"error": str(e)}, status=500)

# def dashboard_proxy(request, model_id, path):
#     """
#     This is just a placeholder - the actual proxying is done by the middleware
#     """
#     # This function should never be called directly as the middleware will intercept the request
#     return HttpResponse("Dashboard proxy error. Middleware not working properly.", status=500)

# def is_port_available(port):
#     with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
#         return sock.connect_ex(('localhost', port)) != 0


# def get_assigned_port(model_instance):
#     if model_instance.port and is_port_available(model_instance.port):
#         return model_instance.port

#     used_ports = Model.objects.exclude(port__isnull=True).values_list('port', flat=True)
#     for port in range(BASE_PORT, BASE_PORT + MAX_DASHBOARDS):
#         if port not in used_ports and is_port_available(port):
#             model_instance.port = port
#             model_instance.save()
#             return port

#     raise Exception("No available ports to assign!")


# def index(request):
#     return render(request, "machine_learning/index.html")


# def launch_dashboard_async(model_id, port):
#     """
#     Background task to launch dashboard.
#     """
#     try:
#         runModel(str(model_id), port)
#     except Exception as e:
#         logger.error(f"Failed to launch dashboard for model {model_id} on port {port}: {str(e)}")


# def dashboard(request, pk):
#     """
#     API endpoint to start dashboard for model <pk>.
#     Returns the dynamic dashboard proxy URL.
#     """
#     try:
#         model_instance = Model.objects.get(id=pk)

#         port = get_assigned_port(model_instance)

#         logger.info(f"Launching dashboard for model {pk} on port {port}")

#         # Launch dashboard in background (non-blocking)
#         threading.Thread(target=launch_dashboard_async, args=(pk, port), daemon=True).start()

#         return JsonResponse({
#             "response": "Success",
#             "dashboard_url": f"/dashboard-proxy/{pk}/",
#             "port": port
#         })

#     except Exception as e:
#         logger.error(f"Error in dashboard view: {str(e)}")
#         traceback.print_exc()
#         return JsonResponse({"error": str(e)}, status=500)

# class ModelViewSet(viewsets.ViewSet):

#     def list(self, request):
#         models = Model.objects.all().order_by('-id')
#         serializer = ModelSerializer(models, many=True)
#         return Response(serializer.data)

#     def create(self, request):
#         try:
#             serializer = ModelSerializer(data=request.data)
#             if serializer.is_valid():
#                 model_instance = serializer.save()
#                 # Save the model ID globally if needed
#                 global saved_id
#                 saved_id = model_instance.id
#                 result = get_review(model_instance.data_set.path)
                
#                 description = ModelDescription.objects.create(
#                     model=model_instance, description={})
#                 description_serializer = ModelDescriptionSerializer(description)
                
#                 # Optionally assign a port to the new model if it is to be among the last 30 dashboards
#                 port = get_assigned_port(model_instance)
#                 model_instance.port = port
#                 model_instance.save()

#                 return Response(
#                     {"response": result, 
#                      "model": serializer.data, 
#                      "description": description_serializer.data,
#                      "port": port
#                      })
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             traceback.print_exc()

#     def destroy(self, request, pk):
#         Model.objects.get(id=pk).delete()
#         models = Model.objects.all().order_by('-id')
#         serializer = ModelSerializer(models, many=True)
#         return Response(serializer.data)
    
#     def open(self, request, pk):
#         """
#         Opens the dashboard for the specified model on its assigned port.
#         """
#         # In the open method of ModelViewSet
#         try:
#             model_instance = Model.objects.get(id=pk)
#             port = get_assigned_port(model_instance)
            
#             # Add file existence check
#             yaml_file = f"{pk}.yaml"
#             if not os.path.exists(yaml_file):
#                 return Response({"error": f"Configuration file {yaml_file} not found"}, status=404)
                
#             if not model_instance.port:
#                 model_instance.port = port
#                 model_instance.save()
#             # Kill any process on the port before launching
#             os.system("npx kill-port " + str(port))
#             # Here we assume you have a YAML config file named <pk>.yaml for this dashboard.
#             os.system('explainerdashboard run ' + str(pk) + '.yaml --no-browser --port=' + str(port))
#             return Response({"response": "Success", "port": port})
#         except Exception as e:
#             traceback.print_exc()
#             return Response({"error": str(e)}, status=500)

# class ModelDescriptionViewSet(viewsets.ViewSet):

#     def update(self, request, pk):
#         description = ModelDescription.objects.get(id=pk)
#         serializer = ModelDescriptionSerializer(description, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class FlaskModelViewSet(viewsets.ViewSet):
#     """
#     This viewset launches the dashboard (for classification or regression) on a unique port.
#     Expected JSON input example:
#     {
#       "model": 12, 
#       "id_column": "Survived", 
#       "prediction_column": "PassengerId", 
#       "not_to_use_columns": ["Name"],
#       "projectTitle": "test", 
#       "algo": "", 
#       "auto": 1, 
#       "unit": "", 
#       "description": 12,
#       "split": "0.2",
#       "label0": "",
#       "label1": ""
#     }
#     """
#     def list(self, request):
#         models = Model.objects.all().order_by('-id')
#         for each_item in models:
#             if each_item.model_type == "RG":
#                 each_item.model_type = "Regression"
#             else:
#                 each_item.model_type = "Classification"
#         serializer = ModelSerializer(models, many=True)
#         return Response(serializer.data)

#     def create(self, request):
#         try:
#             model_obj = Model.objects.get(id=request.data["model"])
#             model_id = request.data["model"]
            
#             # Log the start of model creation
#             logger.info(f"Starting model creation for ID: {model_id}")
            
#             model_type = model_obj.model_type  # 'CL' for classification or 'RG' for regression
#             description_obj = ModelDescription.objects.get(id=request.data["description"])
#             train_csv_path = model_obj.data_set
#             project_title = request.data["projectTitle"]
#             auto = request.data["auto"]
#             algo = request.data["algo"]
#             model_obj.algorithm_name = algo
#             model_obj.save()
#             if algo == "":
#                 algo = "auto"
#             id_column = request.data.get("id_column", "null") or "null"
#             predict = request.data.get("prediction_column", "null") or "null"
#             drop = request.data.get("not_to_use_columns", ["null"]) or ["null"]

#             descriptions = description_obj.description
#             unit = request.data.get("unit", "null") or "null"
#             label0 = request.data.get("label0", "null") or "null"
#             label1 = request.data.get("label1", "null") or "null"
#             split = request.data.get("split", "null") or "null"

#             # Assign a unique port for this model
#             port = get_assigned_port(model_obj)
#             if not model_obj.port:
#                 model_obj.port = port
#                 model_obj.save()

#             # Run the dashboard in a separate thread so that it does not block the request
#             p = threading.Thread(target=self.run,
#                                args=(train_csv_path, project_title, auto, id_column, predict, drop, descriptions, algo,
#                                    model_id, model_type, unit, label0, label1, split, port))
#             p.start()
#             p.join()
            
#             # Define absolute paths for model files
#             base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#             joblib_path = os.path.join(base_dir, f"{model_id}.joblib")
#             yaml_path = os.path.join(base_dir, f"{model_id}.yaml")
            
#             logger.info(f"Expected joblib path: {joblib_path}")
#             logger.info(f"Expected yaml path: {yaml_path}")
            
#             # Check if files were created
#             if os.path.exists(joblib_path):
#                 logger.info(f"Joblib file created successfully at: {joblib_path}")
#                 file_size = os.path.getsize(joblib_path)
#                 logger.info(f"Joblib file size: {file_size} bytes")
#             else:
#                 logger.error(f"Joblib file not found at: {joblib_path}")
            
#             if os.path.exists(yaml_path):
#                 logger.info(f"YAML file created successfully at: {yaml_path}")
#                 file_size = os.path.getsize(yaml_path)
#                 logger.info(f"YAML file size: {file_size} bytes")
#             else:
#                 logger.error(f"YAML file not found at: {yaml_path}")
            
#             # List directory contents
#             dir_contents = os.listdir(base_dir)
#             logger.info(f"Directory contents: {dir_contents}")
            
#             return Response(data={"message": "success", "port": port}, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             logger.error(f"Error in model creation: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def run(self, train_csv_path, project_title, auto, id_column, predict, drop, descriptions, algo, model_id, model_type,
#             unit, label0, label1, split, port):
#         try:
#             base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#             os.chdir(base_dir)  # Change to base directory before running command
            
#             logger.info(f"Current working directory: {os.getcwd()}")
#             logger.info(f"Starting dashboard for Model ID: {model_id} on port {port}")
            
#             # Kill existing process
#             os.system(f"npx kill-port {port}")
            
#             # Construct command with absolute paths
#             if model_type in ['CL']:
#                 command = (
#                     f'python {os.path.join(base_dir, "machine_learning/classifier_custom_explainer.py")} '
#                     f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
#                     f'"{descriptions}" {algo} {model_id} "{label0}" "{label1}" "{split}" --port {port}'
#                 )
#             else:
#                 command = (
#                     f'python {os.path.join(base_dir, "machine_learning/regression_custom_explainer.py")} '
#                     f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
#                     f'"{descriptions}" {algo} {model_id} "{unit}" "{split}" --port {port}'
#                 )
            
#             logger.info(f"Executing command: {command}")
#             result = os.system(command)
#             logger.info(f"Command execution completed with status: {result}")
            
#         except Exception as e:
#             logger.error(f"Error running model {model_id}: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             raise
