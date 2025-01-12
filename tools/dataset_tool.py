import pandas as pd
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from .base import BaseTool
from utils.logger import AgentLogger

class DatasetTool(BaseTool):
    def __init__(self, cache_dir: str = "./cache/datasets"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = AgentLogger()

    def get_description(self) -> str:
        """Implement abstract method from BaseTool"""
        return "Downloads and processes datasets from URLs, with support for various data analysis types"

    async def execute(self, url: str, analysis_type: str = "time_series", **params) -> Dict[str, Any]:
        """Implement abstract method from BaseTool"""
        try:
            # Download dataset
            df = await self.download_dataset(url)
            
            # Process dataset with provided parameters
            result = await self.process_dataset(df, analysis_type, params)
            
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            self.logger.error(f"Dataset operation failed: {str(e)}", "DatasetTool")
            return {
                "success": False,
                "error": str(e)
            }
        
    async def download_dataset(self, url: str) -> pd.DataFrame:
        self.logger.log('INFO', f"Downloading dataset from {url}", "DatasetTool")
        cache_file = self.cache_dir / f"{hash(url)}.csv"
        
        if cache_file.exists():
            self.logger.log('DEBUG', "Using cached dataset", "DatasetTool")
            return pd.read_csv(cache_file)
            
        response = requests.get(url)
        response.raise_for_status()
        
        with cache_file.open('wb') as f:
            f.write(response.content)
            
        return pd.read_csv(cache_file)
        
    async def process_dataset(self, df: pd.DataFrame, analysis_type: str, params: Dict[str, Any]) -> Dict:
        self.logger.tool_call("process_dataset", {"type": analysis_type, "params": params})
        if analysis_type == "time_series":
            return self._process_time_series(df, params)
        # Add other analysis types as needed
        
        raise ValueError(f"Unsupported analysis type: {analysis_type}")
        
    def _process_time_series(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict:
        """Process time series data"""
        date_column = params.get('date_column')
        value_column = params.get('value_column')
        
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
        
        return {
            "type": "time_series",
            "data": df[[date_column, value_column]].to_dict('records')
        }
