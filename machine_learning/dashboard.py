from explainerdashboard import ExplainerDashboard, ExplainerHub
import sys
import joblib
import os

import socket
from contextlib import closing

import logging

# Configure logging
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
    Launches the explainer dashboard for the given model on the specified port.
    It uses the YAML configuration file named '<model_identifier>.yaml'.
    """
    
    def is_port_in_use(port):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            return sock.connect_ex(('localhost', port)) == 0
            
    def find_free_port(start_port):
        port = start_port
        while is_port_in_use(port):
            port += 1
        return port
        
    # Kill any existing process on the port
    os.system(f"npx kill-port {port}")
    
    # Wait a moment for the port to be freed
    import time
    time.sleep(1)
    
    # If port is still in use, find a new one
    if is_port_in_use(port):
        new_port = find_free_port(port)
        logger.info(f"Port {port} in use, switching to port {new_port}")
        port = new_port
    
    yaml_file = f"{model_identifier}.yaml"
    logger.info(f"Loading dashboard from {yaml_file}")
    base_url = os.getenv('API_BASE_URL', 'visautomlbackend-production-0d04.up.railway.app')
    
    try:
        # Load the dashboard from YAML
        dashboard = ExplainerDashboard.from_config(yaml_file)
        
        # Create a hub with the dashboard
        hub = ExplainerHub(
            [dashboard], 
            title=f"Model {model_identifier} Dashboard",
            description="AI Model Analysis Dashboard",
            no_index=False,
            fluid=True,
            bootstrap="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css",
            port=port,
            host="0.0.0.0",
            base_url=f"http://0.0.0.0:{port}/",
        )
        
        # Run the hub
        hub.run(port=port)
        logger.info("Dashboard launched successfully")
    except Exception as e:
        logger.error(f"Error launching dashboard: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
