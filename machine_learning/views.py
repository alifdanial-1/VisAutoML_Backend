import os
import traceback
import threading
from multiprocessing import Process
import pandas as pd

from rest_framework import viewsets, status, decorators, views
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import render
from django.http import JsonResponse

from machine_learning.dashboard import runModel

from .serializers import ModelSerializer, ModelDescriptionSerializer
from .models import Model, ModelDescription  # Make sure Model has a 'port' field (IntegerField, null=True, blank=True)
from .review import get_review
from .regression_custom_explainer import finishing
# from .dashboard import runModel as original_runModel  # We now override runModel below

# Base port and maximum dashboards to run concurrently
BASE_PORT = 8050
MAX_DASHBOARDS = 30

import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('views_operations.log'),
        logging.StreamHandler()
    ]
)

def get_assigned_port(model_instance):
    try:
        logger.info(f"Getting assigned port for model ID: {model_instance.id}")
        if model_instance.port:
            logger.info(f"Using existing port: {model_instance.port}")
            return model_instance.port
        
        last_models = Model.objects.filter(port__isnull=False).order_by('-id')[:MAX_DASHBOARDS]
        assigned_ports = [m.port for m in last_models if m.port is not None]
        logger.info(f"Currently assigned ports: {assigned_ports}")
        
        for port in range(BASE_PORT, BASE_PORT + MAX_DASHBOARDS):
            if port not in assigned_ports:
                logger.info(f"Assigned new port: {port}")
                return port
        
        next_port = max(assigned_ports) + 1 if assigned_ports else BASE_PORT
        logger.info(f"All ports in use, assigning next available port: {next_port}")
        return next_port
    except Exception as e:
        logger.error(f"Error in get_assigned_port: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

class FlaskModelViewSet(viewsets.ViewSet):
    def create(self, request):
        try:
            model_obj = Model.objects.get(id=request.data["model"])
            model_id = request.data["model"]
            logger.info(f"Creating model for ID: {model_id}")
            
            # Log input parameters
            logger.info(f"Project title: {request.data['projectTitle']}")
            logger.info(f"Auto mode: {request.data['auto']}")
            logger.info(f"Algorithm: {request.data['algo']}")
            
            model_type = model_obj.model_type  # 'CL' for classification or 'RG' for regression
            description_obj = ModelDescription.objects.get(id=request.data["description"])
            train_csv_path = model_obj.data_set
            project_title = request.data["projectTitle"]
            auto = request.data["auto"]
            algo = request.data["algo"]
            model_obj.algorithm_name = algo
            model_obj.save()
            if algo == "":
                algo = "auto"
            id_column = request.data.get("id_column", "null") or "null"
            predict = request.data.get("prediction_column", "null") or "null"
            drop = request.data.get("not_to_use_columns", ["null"]) or ["null"]

            descriptions = description_obj.description
            unit = request.data.get("unit", "null") or "null"
            label0 = request.data.get("label0", "null") or "null"
            label1 = request.data.get("label1", "null") or "null"
            split = request.data.get("split", "null") or "null"

            # Assign a unique port for this model
            port = get_assigned_port(model_obj)
            logger.info(f"Assigned port {port} to model {model_id}")
            
            if not model_obj.port:
                model_obj.port = port
                model_obj.save()
                logger.info(f"Saved port {port} to model {model_id}")
            
            # Run dashboard thread
            p = threading.Thread(target=self.run,
                               args=(train_csv_path, project_title, auto, id_column, predict, drop, 
                                     descriptions, algo, model_id, model_type, unit, label0, 
                                     label1, split, port))
            p.start()
            logger.info(f"Started dashboard thread for model {model_id}")
            p.join()
            
            return Response({"status": "success", "message": f"Model {model_id} created successfully"})
            
        except Exception as e:
            logger.error(f"Error creating model {model_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({"status": "error", "message": str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def run(self, train_csv_path, project_title, auto, id_column, predict, drop, descriptions, 
            algo, model_id, model_type, unit, label0, label1, split, port):
        try:
            logger.info(f"Starting run for model {model_id} on port {port}")
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            os.chdir(base_dir)
            
            logger.info(f"Working directory: {os.getcwd()}")
            
            # Kill existing process
            os.system(f"npx kill-port {port}")
            logger.info(f"Killed existing process on port {port}")
            
            # Construct and execute command
            if model_type in ['CL']:
                command = (
                    f'python {os.path.join(base_dir, "machine_learning/classifier_custom_explainer.py")} '
                    f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
                    f'"{descriptions}" {algo} {model_id} "{label0}" "{label1}" "{split}" --port {port}'
                )
            else:
                command = (
                    f'python {os.path.join(base_dir, "machine_learning/regression_custom_explainer.py")} '
                    f'{train_csv_path} "{project_title}" {auto} "{id_column}" "{predict}" "{drop}" '
                    f'"{descriptions}" {algo} {model_id} "{unit}" "{split}" --port {port}'
                )
            
            logger.info(f"Executing command: {command}")
            result = os.system(command)
            logger.info(f"Command execution completed with status: {result}")
            
        except Exception as e:
            logger.error(f"Error in run method for model {model_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
