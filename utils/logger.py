import logging
from typing import Optional
import os
import sys
from config.config import get_config

# Dictionary to store loggers by name
_loggers = {}

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name (str): Name for the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    global _loggers
    
    # Return existing logger if already configured
    if name in _loggers:
        return _loggers[name]
    
    # Create and configure a new logger
    logger = logging.getLogger(name)
    
    # Only configure the logger if it hasn't been configured yet
    if not logger.handlers:
        # Get log level from config or default to INFO
        try:
            config = get_config()
            log_level_str = config.get("log_level", "INFO")
        except:
            # If config isn't initialized yet, use default
            log_level_str = os.environ.get("LOG_LEVEL", "INFO")
        
        # Convert string level to logging constant
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # Set logger level
        logger.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        # Try to create a file handler if not in debug mode
        if log_level != logging.DEBUG:
            try:
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                
                file_handler = logging.FileHandler(
                    os.path.join(log_dir, f"{name.replace('.', '_')}.log")
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # Just log to console if file logging fails
                console_handler.setLevel(logging.DEBUG)
                logger.warning(f"Could not set up file logging: {str(e)}")
        
    # Store the logger
    _loggers[name] = logger
    return logger

def configure_root_logger(log_level: Optional[str] = None) -> None:
    """
    Configure the root logger with a specific log level.
    
    Args:
        log_level (str, optional): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if not log_level:
        try:
            config = get_config()
            log_level = config.get("log_level", "INFO")
        except:
            log_level = os.environ.get("LOG_LEVEL", "INFO")
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
