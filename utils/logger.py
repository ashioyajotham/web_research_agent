import logging
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime
from typing import Any, Dict
import json
from logging.handlers import RotatingFileHandler

class CustomFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'context'):
            record.context = ''
        return super().format(record)

class AgentLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main logger
        self.logger = self._setup_main_logger()
        
        # Specialized loggers
        self.metrics_logger = self._setup_specialized_logger("metrics")
        self.performance_logger = self._setup_specialized_logger("performance")
        self.error_logger = self._setup_specialized_logger("errors")

    def _setup_main_logger(self):
        logger = logging.getLogger("WebResearchAgent")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            # Console handler with rich formatting
            console_handler = RichHandler(rich_tracebacks=True, markup=True, show_time=False)
            console_handler.setLevel(logging.INFO)
            
            # Rotating file handler
            file_handler = RotatingFileHandler(
                self.log_dir / f"agent.log",
                maxBytes=10_000_000,
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Formatters
            console_format = logging.Formatter('%(message)s')
            file_format = CustomFormatter('%(asctime)s [%(levelname)s] %(context)s: %(message)s')
            
            console_handler.setFormatter(console_format)
            file_handler.setFormatter(file_format)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger

    def _setup_specialized_logger(self, name: str):
        logger = logging.getLogger(f"WebResearchAgent.{name}")
        logger.setLevel(logging.INFO)
        
        file_handler = RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=10_000_000,
            backupCount=5
        )
        formatter = CustomFormatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

    def log(self, level: str, message: str, context: str = "Agent", exc_info: bool = False):
        """General logging"""
        extra = {'context': context}
        getattr(self.logger, level.lower())(message, extra=extra, exc_info=exc_info)

    def log_metrics(self, task: str, result: Dict[str, Any], metrics: Dict[str, Any]):
        """Metrics logging"""
        self.metrics_logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "success": result.get("success", False),
            "metrics": metrics
        }))

    def log_error(self, error: str, context: Dict[str, Any] = None):
        """Error logging"""
        self.error_logger.error(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "context": context
        }))

    def log_performance(self, metrics: Dict[str, Any]):
        """Performance logging"""
        self.performance_logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **metrics
        }))

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error messages"""
        self.logger.error(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning messages"""
        self.logger.warning(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info messages"""
        self.logger.info(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug messages"""
        self.logger.debug(message, *args, **kwargs)