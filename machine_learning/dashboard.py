from explainerdashboard import ExplainerDashboard
import os

def runModel(filename, port=8050):
    os.environ["DASH_CSP_HEADER_DISABLED"] = "1"

    db = ExplainerDashboard.from_yaml(
        f"{filename}.yaml",
        explainerfile=f"{filename}.joblib",
        allow_remote=True
    )

    db.run(port=port, use_reloader=False)
