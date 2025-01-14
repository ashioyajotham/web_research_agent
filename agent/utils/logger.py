import logging
from typing import Any, Optional, Dict
from datetime import datetime
import json
from pathlib import Path

class AgentLogger:
    def __init__(self, log_dir: str = "logs"):
        # ...existing code...
        
        # Add structured logging
        self.metrics_logger = logging.getLogger("metrics")
        self.error_logger = logging.getLogger("errors")
        self.performance_logger = logging.getLogger("performance")
        
        # Add log rotation
        self._setup_log_rotation()
        
    def log_execution(self, task: str, result: Dict[str, Any], metrics: Dict[str, Any]):
        """Log execution with detailed metrics"""
        execution_log = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "success": result.get("success", False),
            "confidence": result.get("confidence", 0.0),
            "execution_time": metrics.get("execution_time", 0.0),
            "error": result.get("error"),
            "performance_metrics": metrics
        }
        
        self.metrics_logger.info(json.dumps(execution_log))
