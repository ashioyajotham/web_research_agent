from typing import Dict, Tuple, Optional, Union, List
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class NumberUnit(Enum):
    NONE = "none"
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    WEIGHT = "weight"
    VOLUME = "volume"
    LENGTH = "length"
    EMISSIONS = "emissions"
    ENERGY = "energy"

@dataclass
class ProcessedNumber:
    value: float
    original_value: str
    unit: NumberUnit
    confidence: float
    context: str = ""
    normalized_value: Optional[float] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class NumberProcessor:
    def __init__(self):
        self.scale_multipliers = {
            'trillion': 1e12,
            'billion': 1e9,
            'million': 1e6,
            'thousand': 1e3,
            'hundred': 1e2,
            'dozens': 12,
            'k': 1e3,
            'm': 1e6,
            'b': 1e9,
            't': 1e12
        }
        
        self.unit_patterns = {
            NumberUnit.PERCENTAGE: [
                (r'(\d+(?:\.\d+)?)\s*%', 1.0),
                (r'(\d+(?:\.\d+)?)\s*percent(?:age)?', 1.0),
                (r'(\d+(?:\.\d+)?)\s*pts?', 1.0)
            ],
            NumberUnit.CURRENCY: [
                (r'\$\s*(\d+(?:\.\d+)?)', 1.0),
                (r'(\d+(?:\.\d+)?)\s*(?:USD|dollars?)', 1.0),
                (r'£\s*(\d+(?:\.\d+)?)', 1.25),  # Approximate GBP to USD
                (r'€\s*(\d+(?:\.\d+)?)', 1.1)    # Approximate EUR to USD
            ],
            NumberUnit.WEIGHT: [
                (r'(\d+(?:\.\d+)?)\s*(?:kg|kilos?)', 1.0),
                (r'(\d+(?:\.\d+)?)\s*(?:g|grams?)', 0.001),
                (r'(\d+(?:\.\d+)?)\s*(?:t|tons?|tonnes?)', 1000.0)
            ],
            NumberUnit.EMISSIONS: [
                (r'(\d+(?:\.\d+)?)\s*(?:tCO2e?)', 1.0),
                (r'(\d+(?:\.\d+)?)\s*(?:MT|Mt)CO2e?', 1_000_000),
                (r'(\d+(?:\.\d+)?)\s*(?:GT)CO2e?', 1_000_000_000)
            ],
            NumberUnit.ENERGY: [
                (r'(\d+(?:\.\d+)?)\s*(?:kWh)', 1.0),
                (r'(\d+(?:\.\d+)?)\s*(?:MWh)', 1000.0),
                (r'(\d+(?:\.\d+)?)\s*(?:GWh)', 1_000_000)
            ]
        }
        
        self.context_patterns = {
            'increase': r'(?:increase|growth|rise|grew|up|higher)\s+(?:by|of|to)?\s*',
            'decrease': r'(?:decrease|decline|fall|fell|down|lower)\s+(?:by|of|to)?\s*',
            'comparison': r'(?:compared|relative|vs|versus)\s+(?:to|with)\s*',
            'time_period': r'(?:in|during|for|since|until)\s+(?:20\d{2}|Q[1-4]|[12][0-9]{3})'
        }

    def extract_numbers(self, text: str, unit_type: Optional[NumberUnit] = None) -> List[ProcessedNumber]:
        """Extract numbers with units from text"""
        numbers = []
        
        # First look for scale indicators
        text = self._normalize_scale_words(text)
        
        # Process based on unit type if specified
        if unit_type:
            patterns = self.unit_patterns.get(unit_type, [])
            for pattern, multiplier in patterns:
                numbers.extend(self._extract_with_pattern(text, pattern, multiplier, unit_type))
        else:
            # Try all patterns if no specific unit type
            for unit_type, patterns in self.unit_patterns.items():
                for pattern, multiplier in patterns:
                    numbers.extend(self._extract_with_pattern(text, pattern, multiplier, unit_type))
        
        # Add context to each number
        for num in numbers:
            num.context = self._extract_context(text, num.original_value)
        
        return sorted(numbers, key=lambda x: x.confidence, reverse=True)

    def calculate_change(self, old_value: ProcessedNumber, new_value: ProcessedNumber) -> ProcessedNumber:
        """Calculate percentage change between two numbers"""
        try:
            if old_value.value == 0:
                if new_value.value == 0:
                    percentage = 0
                else:
                    percentage = float('inf')
            else:
                percentage = ((new_value.value - old_value.value) / old_value.value) * 100
            
            return ProcessedNumber(
                value=percentage,
                original_value=f"{percentage:,.2f}%",
                unit=NumberUnit.PERCENTAGE,
                confidence=min(old_value.confidence, new_value.confidence),
                context=f"Change from {old_value.original_value} to {new_value.original_value}",
                metadata={
                    'old_value': old_value.value,
                    'new_value': new_value.value,
                    'old_unit': old_value.unit,
                    'new_unit': new_value.unit
                }
            )
        except Exception as e:
            logger.error(f"Error calculating change: {str(e)}")
            return None

    def normalize_number(self, number: ProcessedNumber) -> ProcessedNumber:
        """Normalize number to standard unit"""
        try:
            if number.unit == NumberUnit.EMISSIONS:
                # Normalize to tCO2e
                number.normalized_value = number.value
                if 'Mt' in number.original_value or 'MT' in number.original_value:
                    number.normalized_value *= 1_000_000
                elif 'Gt' in number.original_value or 'GT' in number.original_value:
                    number.normalized_value *= 1_000_000_000
            elif number.unit == NumberUnit.CURRENCY:
                # Normalize to USD
                number.normalized_value = number.value
                if '€' in number.original_value:
                    number.normalized_value *= 1.1
                elif '£' in number.original_value:
                    number.normalized_value *= 1.25
            
            return number
            
        except Exception as e:
            logger.error(f"Error normalizing number: {str(e)}")
            return number

    def format_number(self, number: ProcessedNumber, format_type: str = 'standard') -> str:
        """Format number for display"""
        try:
            if format_type == 'standard':
                return f"{number.value:,.2f}"
            elif format_type == 'compact':
                if abs(number.value) >= 1e9:
                    return f"{number.value/1e9:.1f}B"
                elif abs(number.value) >= 1e6:
                    return f"{number.value/1e6:.1f}M"
                elif abs(number.value) >= 1e3:
                    return f"{number.value/1e3:.1f}K"
                return f"{number.value:.1f}"
            elif format_type == 'full':
                unit_symbol = ''
                if number.unit == NumberUnit.PERCENTAGE:
                    unit_symbol = '%'
                elif number.unit == NumberUnit.CURRENCY:
                    unit_symbol = 'USD'
                elif number.unit == NumberUnit.EMISSIONS:
                    unit_symbol = 'tCO2e'
                return f"{number.value:,.2f} {unit_symbol}".strip()
                
            return str(number.value)
            
        except Exception as e:
            logger.error(f"Error formatting number: {str(e)}")
            return str(number.value)

    def _normalize_scale_words(self, text: str) -> str:
        """Convert scale words to numerical representations"""
        for scale_word, multiplier in self.scale_multipliers.items():
            # Use word boundaries to avoid partial matches
            pattern = rf'\b(\d+(?:\.\d+)?)\s*{scale_word}\b'
            text = re.sub(pattern, lambda m: str(float(m.group(1)) * multiplier), text, flags=re.IGNORECASE)
        return text

    def _extract_with_pattern(self, text: str, pattern: str, multiplier: float, unit_type: NumberUnit) -> List[ProcessedNumber]:
        """Extract numbers using a specific pattern"""
        numbers = []
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                value = float(match.group(1)) * multiplier
                original = match.group(0)
                
                # Calculate confidence based on context
                confidence = self._calculate_confidence(text, original, unit_type)
                
                numbers.append(ProcessedNumber(
                    value=value,
                    original_value=original,
                    unit=unit_type,
                    confidence=confidence
                ))
                
            except (ValueError, InvalidOperation) as e:
                logger.debug(f"Failed to parse number: {str(e)}")
                continue
                
        return numbers

    def _calculate_confidence(self, text: str, number_str: str, unit_type: NumberUnit) -> float:
        """Calculate confidence score for extracted number"""
        confidence = 0.5  # Base confidence
        
        # Check for exact unit match
        if unit_type != NumberUnit.NONE:
            confidence += 0.2
        
        # Check for contextual indicators
        context_boost = 0.0
        for context_type, pattern in self.context_patterns.items():
            if re.search(pattern + number_str, text, re. IGNORECASE):
                context_boost += 0.1
        return confidence