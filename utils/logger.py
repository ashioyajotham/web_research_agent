import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime
from typing import Any, Dict
from logging.handlers import RotatingFileHandler
import asyncio
from functools import wraps

class AsyncSafeFormatter(logging.Formatter):
    def format(self, record):
        # Ensure context exists
        if not hasattr(record, 'context'):
            record.context = 'Agent'
        
        # Handle async context
        try:
            task = asyncio.current_task()
            if task:
                record.async_task = task.get_name()
        except RuntimeError:
            record.async_task = 'MainThread'
            
        return super().format(record)

class AgentLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize loggers
        self.logger = self._setup_main_logger()
        self.metrics_logger = self._setup_specialized_logger("metrics")
        self.error_logger = self._setup_specialized_logger("errors")
        self.performance_logger = self._setup_specialized_logger("performance")

    def _setup_main_logger(self):
        logger = logging.getLogger("WebResearchAgent")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            # Console handler
            console_handler = RichHandler(rich_tracebacks=True)
            console_handler.setLevel(logging.INFO)
            
            # File handler
            file_handler = RotatingFileHandler(
                self.log_dir / "agent.log",
                maxBytes=10_000_000,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Formatters
            console_format = "%(message)s"
            file_format = "%(asctime)s [%(levelname)s] %(context)s: %(message)s"
            
            console_handler.setFormatter(AsyncSafeFormatter(console_format))
            file_handler.setFormatter(AsyncSafeFormatter(file_format))
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger

    def _setup_specialized_logger(self, name: str):
        logger = logging.getLogger(f"WebResearchAgent.{name}")
        logger.setLevel(logging.INFO)
        
        handler = RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=10_000_000,
            backupCount=5
        )
        
        formatter = AsyncSafeFormatter(
            "%(asctime)s - %(context)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

    async def log(self, level: str, message: str, context: str = "Agent", exc_info: bool = False):
        """Async-safe logging"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: getattr(self.logger, level.lower())(
                message,
                extra={"context": context},
                exc_info=exc_info
            )
        )

    async def log_metrics(self, task: str, result: Dict[str, Any], metrics: Dict[str, Any]):
        """Async-safe metrics logging"""
        message = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "metrics": metrics
        }
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.metrics_logger.info,
            str(message),
            extra={"context": "Metrics"}
        )

    async def log_error(self, error: str, context: Dict[str, Any] = None):
        """Async-safe error logging"""
        await self.log("error", error, context=str(context), exc_info=True)

    async def log_performance(self, metrics: Dict[str, Any]):
        """Async-safe performance logging"""
        message = {
            "timestamp": datetime.now().isoformat(),
            **metrics
        }
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.performance_logger.info,
            str(message),
            extra={"context": "Performance"}
        )

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