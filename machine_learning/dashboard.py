from explainerdashboard import ExplainerDashboard
import sys
import joblib
import os

def runModel(model_identifier, port):
    """
    Launches the explainer dashboard for the given model on the specified port.
    It uses the YAML configuration file named '<model_identifier>.yaml'.
    """
    yaml_file = f"{model_identifier}.yaml"
    base_url = os.getenv('API_BASE_URL', 'visautomlbackend-production-0d04.up.railway.app')
    os.system(f"explainerdashboard run {yaml_file} --no-browser --port={port} "
             f"--host=0.0.0.0 --url-base-pathname=/model/{model_identifier}/")
