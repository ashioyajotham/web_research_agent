import pandas as pd
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from .base import BaseTool
from utils.logger import AgentLogger
import io
import json
import logging

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
        
        # Detect file type from content or URL
        if url.endswith('.csv'):
            return pd.read_csv(io.StringIO(response.text))
        elif url.endswith('.json'):
            return pd.read_json(io.StringIO(response.text))
        elif url.endswith('.xlsx'):
            return pd.read_excel(io.BytesIO(response.content))
        else:
            # Try to parse as CSV first, then JSON
            try:
                return pd.read_csv(io.StringIO(response.text))
            except:
                return pd.read_json(io.StringIO(response.text))
        
    async def process_dataset(self, df: pd.DataFrame, analysis_type: str, params: Dict[str, Any]) -> Dict:
        self.logger.tool_call("process_dataset", {"type": analysis_type, "params": params})
        try:
            if analysis_type == "time_series":
                return self._analyze_time_series(df, params)
            elif analysis_type == "statistical":
                return self._analyze_statistical(df, params)
            elif analysis_type == "comparative":
                return self._analyze_comparative(df, params)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
                
        except Exception as e:
            logging.error(f"Dataset processing failed: {str(e)}")
            raise

    def _analyze_time_series(self, df: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Analyze time series data"""
        # Sort by date if available
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0:
            df = df.sort_values(date_cols[0])
            
        # Handle different aggregation types
        agg_type = params.get('aggregate', 'max')
        if agg_type == 'max':
            result = df.max()
        elif agg_type == 'min':
            result = df.min()
        else:
            result = df.mean()
            
        return {
            "type": "time_series",
            "data": result.to_dict(),
            "metadata": {
                "rows": len(df),
                "columns": list(df.columns)
            }
        }

    def _analyze_statistical(self, df: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Perform statistical analysis"""
        return {
            "type": "statistical",
            "summary": df.describe().to_dict(),
            "correlations": df.corr().to_dict() if len(df.select_dtypes(include=['number']).columns) > 1 else None
        }

    def _analyze_comparative(self, df: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Perform comparative analysis"""
        group_by = params.get('group_by')
        if group_by and group_by in df.columns:
            return {
                "type": "comparative",
                "groups": df.groupby(group_by).mean().to_dict()
            }
        return {
            "type": "comparative",
            "error": "No valid grouping column specified"
        }
