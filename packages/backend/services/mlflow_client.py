"""MLflow client for backend. Phase 1: no-op."""

from acs_shared.settings import settings


class MLflowClient:
    """Client for MLflow experiment tracking. Phase 1: no-op."""

    def __init__(self):
        self.uri = settings.mlflow_tracking_uri

    async def log_run(self, *args, **kwargs):
        """Log a run to MLflow. Phase 1: no-op."""
        pass
