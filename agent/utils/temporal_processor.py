from datetime import datetime, timedelta
from typing import Optional, Tuple, Union
import logging
import re
from dateutil import parser

class TemporalProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Generic temporal patterns
        self.patterns = {
            'absolute': [
                r'(?:on|in|at)\s+([^,.]+\d{4})',
                r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})',
                r'(\d{4})'
            ],
            'relative': [
                r'(\d+)\s*(?:day|week|month|year)s?\s+(?:ago|before|after)',
                r'(?:last|next|this)\s+(?:day|week|month|year)',
                r'(?:yesterday|today|tomorrow)'
            ],
            'duration': [
                r'(?:for|during)\s+(\d+)\s*(?:day|week|month|year)s?',
                r'between\s+([^,]+)\s+and\s+([^,]+)'
            ]
        }

    def parse_time_range(self, time_str: str) -> Tuple[datetime, datetime]:
        """Parse any time range from string input"""
        try:
            now = datetime.now()
            
            # Handle relative times
            if match := re.search(self.patterns['relative'], time_str.lower()):
                return self._handle_relative_time(match.group(), now)
            
            # Handle durations
            if match := re.search(self.patterns['duration'], time_str.lower()):
                return self._handle_duration(match, now)
            
            # Handle explicit dates
            if match := re.search(self.patterns['absolute'], time_str):
                return self._handle_explicit_date(match.group())
            
            # Handle periods
            if match := re.search(self.patterns['duration'], time_str):
                return self._handle_period(match.group(1), now)
            
            raise ValueError(f"Unsupported time format: {time_str}")
            
        except Exception as e:
            self.logger.error(f"Error parsing time range: {e}")
            raise

    def _handle_relative_time(self, relative: str, now: datetime) -> Tuple[datetime, datetime]:
        """Handle relative time expressions"""
        if 'today' in relative:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif 'yesterday' in relative:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    def is_within_timeframe(self, check_time: datetime, reference_period: str) -> bool:
        """Check if a given time falls within a reference period"""
        start, end = self.parse_time_range(reference_period)
        return start <= check_time <= end

    def get_time_difference(self, time1: datetime, time2: datetime) -> timedelta:
        """Calculate the absolute time difference between two timestamps"""
        return abs(time1 - time2)

    def extract_temporal_info(self, text: str) -> Optional[datetime]:
        """Extract temporal information from text"""
        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                if matches := re.findall(pattern, text, re.IGNORECASE):
                    try:
                        # Handle different types of temporal references
                        if pattern_type == 'absolute':
                            return self._parse_absolute_date(matches[0])
                        elif pattern_type == 'relative':
                            return self._handle_relative_date(matches[0])
                        elif pattern_type == 'duration':
                            return self._handle_duration(matches[0])
                    except Exception as e:
                        self.logger.debug(f"Failed to parse {pattern_type} date: {e}")
                        continue
        return None

    def _parse_absolute_date(self, date_str: str) -> Optional[datetime]:
        """Parse absolute date references"""
        try:
            return parser.parse(date_str, fuzzy=True)
        except Exception as e:
            self.logger.debug(f"Date parsing failed: {e}")
            return None

    def _extract_temporal_info(self, query: str) -> datetime:
        """Extract temporal information from a query string"""
        try:
            # Look for date patterns in the query
            date_matches = re.findall(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', query)
            if date_matches:
                return parser.parse(date_matches[0])
            
            # Handle relative dates
            if 'today' in query.lower():
                return datetime.now()
            elif 'yesterday' in query.lower():
                return datetime.now() - timedelta(days=1)
            
            # Default to current time if no temporal info found
            return datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to extract temporal info: {e}")
            raise
