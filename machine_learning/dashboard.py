# dashboard.py
import os
import joblib
import traceback
import logging
from explainerdashboard import ExplainerDashboard, ExplainerHub

logger = logging.getLogger(__name__)

def runModel(model_identifier, port):
    """
    Launches the ExplainerDashboard on the provided port using saved YAML and joblib.
    This function assumes the YAML config is named '<model_identifier>.yaml'.
    """
    yaml_file = f"{model_identifier}.yaml"

    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    try:
        logger.info(f"Loading dashboard for model {model_identifier} on port {port}")
        
        # Load dashboard from config
        dashboard = ExplainerDashboard.from_config(yaml_file)
        
        # Create hub with the dashboard
        hub = ExplainerHub(
            [dashboard],
            title=f"Model {model_identifier} Dashboard",
            description="AI Model Analysis Dashboard",
            no_index=True,
            fluid=True,
            bootstrap="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css",
        )
        
        # Get base URL from environment - for Railway
        # This ensures the dashboard is aware of its public URL
        base_url = os.getenv('BASE_URL', '')
        
        # Start the dashboard - on Railway, we need to bind to 0.0.0.0
        hub.run(
            port=port, 
            host="0.0.0.0",
            use_waitress=True,  # More production-ready WSGI server
            debug=False
        )
        
    except Exception as e:
        logger.error(f"Error launching dashboard for model {model_identifier} on port {port}")
        logger.error(f"{str(e)}\n{traceback.format_exc()}")
        raise