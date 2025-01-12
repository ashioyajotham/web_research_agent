import logging
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime

class AgentLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger("WebResearchAgent")
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler with rich formatting
            console_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=False
            )
            console_handler.setLevel(logging.INFO)
            
            # File handler for detailed logs
            file_handler = logging.FileHandler(
                self.log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Formatters
            console_format = logging.Formatter('%(message)s')
            file_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(context)s: %(message)s'
            )
            
            console_handler.setFormatter(console_format)
            file_handler.setFormatter(file_format)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str, context: str = "Agent"):
        """Log a message with context"""
        extra = {'context': context}
        getattr(self.logger, level.lower())(message, extra=extra)
        
    def task_start(self, task: str):
        self.log('INFO', f"Starting task: {task}", "TaskManager")
        
    def task_complete(self, task: str, time_taken: float):
        self.log('INFO', f"Completed task in {time_taken:.2f}s", "TaskManager")
        
    def tool_call(self, tool: str, params: dict):
        self.log('DEBUG', f"Calling tool {tool} with params: {params}", "ToolManager")
        
    def error(self, error: str, context: str = "Error"):
        self.log('ERROR', str(error), context)
