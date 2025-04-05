from explainerdashboard import ExplainerDashboard, ExplainerHub
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
