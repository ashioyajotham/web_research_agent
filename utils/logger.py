import logging
import os
from pathlib import Path
import sys

# Global logger configuration
_logger_configured = False
_log_level = logging.WARNING  # Default to WARNING instead of INFO

def configure_logging(log_level=None):
    """Configure logging for the application."""
    global _logger_configured, _log_level
    
    if log_level:
        _log_level = log_level
    
    if _logger_configured:
        return
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(_log_level)
    
    # Console handler with less verbose output (WARNING+)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handlers for more comprehensive logging
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                                   datefmt='%Y-%m-%d %H:%M:%S')
    
    # Main log file with all logs
    file_handler = logging.FileHandler(logs_dir / "agent.log")
    file_handler.setLevel(_log_level)  # Use the configured log level
    file_handler.setFormatter(file_format)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Additional log files for specific components
    components = ["agent", "tools", "utils", "config"]
    for component in components:
        component_logger = logging.getLogger(component)
        component_handler = logging.FileHandler(logs_dir / f"{component}.log")
        component_handler.setFormatter(file_format)
        component_handler.setLevel(_log_level)
        component_logger.addHandler(component_handler)
    
    _logger_configured = True

def get_logger(name):
    """Get a logger with the given name."""
    if not _logger_configured:
        configure_logging()
    
    return logging.getLogger(name)

def set_log_level(level):
    """Set the log level for all loggers."""
    global _log_level
    
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    _log_level = level
    
    # Update root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Update all handlers
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):  # Keep file handlers at the set level
            handler.setLevel(level)
    
    # Update component loggers
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(level)
