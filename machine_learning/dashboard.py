from explainerdashboard import ExplainerDashboard, ExplainerHub
import sys
import joblib
import os

import socket
from contextlib import closing


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
        port = find_free_port(port)
    
    yaml_file = f"{model_identifier}.yaml"
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
            base_url=f"/model/{model_identifier}/",
        )
        
        # Run the hub
        hub.run(port=port)
    except Exception as e:
        print(f"Error launching dashboard: {str(e)}")
        raise
