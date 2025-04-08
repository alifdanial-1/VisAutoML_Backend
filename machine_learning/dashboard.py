# from explainerdashboard import ExplainerDashboard, ExplainerHub
# import sys
# import joblib
# import os

# import socket
# from contextlib import closing

# from .models import PortRegistry
# import logging

# # Configure logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('dashboard_operations.log'),
#         logging.StreamHandler()
#     ]
# )
# def get_available_port(start=8000, end=9000):
#     for port in range(start, end):
#         if not PortRegistry.objects.filter(port=port, in_use=True).exists():
#             PortRegistry.objects.create(port=port, in_use=True)
#             return port
#     raise Exception("No available ports")


# def runModel(model_identifier, port):
#     """
#     Launches the explainer dashboard for the given model on the specified port.
#     It uses the YAML configuration file named '<model_identifier>.yaml'.
#     """
    
#     # def is_port_in_use(port):
#     #     with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
#     #         return sock.connect_ex(('localhost', port)) == 0
            
#     # def find_free_port(start_port):
#     #     port = start_port
#     #     while is_port_in_use(port):
#     #         port += 1
#     #     return port
        
#     # # Kill any existing process on the port
#     # os.system(f"npx kill-port {port}")
    
#     # # Wait a moment for the port to be freed
#     # import time
#     # time.sleep(1)
    
#     # # If port is still in use, find a new one
#     # if is_port_in_use(port):
#     #     new_port = find_free_port(port)
#     #     logger.info(f"Port {port} in use, switching to port {new_port}")
#     #     port = new_port
    
#     yaml_file = f"{model_identifier}.yaml"
#     logger.info(f"Loading dashboard from {yaml_file}")
#     base_url = os.getenv('API_BASE_URL', 'visautomlbackend-production-0d04.up.railway.app')
#     port = get_available_port()
#     logger.info(f"Launching dashboard on port {port}")
#     try:
#         # Load the dashboard from YAML
#         dashboard = ExplainerDashboard.from_config(yaml_file)
        
#         # Create a hub with the dashboard
#         hub = ExplainerHub(
#             [dashboard], 
#             title=f"Model {model_identifier} Dashboard",
#             description="AI Model Analysis Dashboard",
#             no_index=False,
#             fluid=True,
#             bootstrap="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css",
#             port=port,
#             host="0.0.0.0",
#             base_url=f"http://0.0.0.0:{port}/",
#         )
        
#         # Run the hub
#         hub.run(port=port)
#         logger.info("Dashboard launched successfully")
#     except Exception as e:
#         logger.error(f"Error launching dashboard: {str(e)}")
#         logger.error(f"Traceback: {traceback.format_exc()}")
#         raise

import os
import joblib
import traceback
import logging

from explainerdashboard import ExplainerDashboard, ExplainerHub

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard_operations.log'),
        logging.StreamHandler()
    ]
)

def runModel(model_identifier, port):
    """
    Launches the ExplainerDashboard on the provided port using saved YAML and joblib.
    This function assumes the YAML config is named '<model_identifier>.yaml'.
    """
    yaml_file = f"{model_identifier}.yaml"

    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    try:
        logger.info(f"Loading dashboard from config: {yaml_file}")

        dashboard = ExplainerDashboard.from_config(yaml_file)

        hub = ExplainerHub(
            [dashboard],
            title=f"Model {model_identifier} Dashboard",
            description="AI Model Analysis Dashboard",
            no_index=True,
            fluid=True,
            bootstrap="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css",
        )

        logger.info(f"Starting dashboard for model {model_identifier} on port {port}")
        hub.run(port=port, host="0.0.0.0")

    except Exception as e:
        logger.error(f"Error launching dashboard for model {model_identifier} on port {port}")
        logger.error(f"{str(e)}\n{traceback.format_exc()}")
        raise
