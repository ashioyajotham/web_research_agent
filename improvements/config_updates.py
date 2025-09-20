# Add these to your config.py or config.yaml

# Presentation tool settings
PRESENTATION_CONFIG = {
    "max_content_items": 5,  # Maximum number of content items to process
    "max_answer_sentences": 2,  # Maximum sentences for factual answers
    "max_sources": 5,  # Maximum sources to cite
    "content_preview_length": 300,  # Length for content previews
    "enable_detailed_logging": True,  # Enable detailed logging
    "fallback_on_extraction_failure": True,  # Use fallback when extraction fails
}

# Question type detection settings
QUESTION_TYPE_CONFIG = {
    "confidence_threshold": 0.7,  # Minimum confidence for question type detection
    "default_type": "general",  # Default when type detection fails
    "enable_pattern_matching": True,  # Use regex patterns for type detection
}

# Content processing settings
CONTENT_PROCESSING_CONFIG = {
    "min_content_length": 20,  # Minimum content length to consider
    "max_content_length": 2000,  # Maximum content length to process
    "enable_light_cleaning": True,  # Enable light content cleaning
    "preserve_source_info": True,  # Always preserve source information
}

# In your main config loading
def load_presentation_config():
    """Load presentation tool configuration."""
    config = {
        **PRESENTATION_CONFIG,
        **QUESTION_TYPE_CONFIG,
        **CONTENT_PROCESSING_CONFIG,
    }
    
    # Override with environment variables if available
    for key, default_value in config.items():
        env_key = f"PRESENTATION_{key.upper()}"
        if env_key in os.environ:
            if isinstance(default_value, bool):
                config[key] = os.environ[env_key].lower() == 'true'
            elif isinstance(default_value, int):
                config[key] = int(os.environ[env_key])
            else:
                config[key] = os.environ[env_key]
    
    return config
