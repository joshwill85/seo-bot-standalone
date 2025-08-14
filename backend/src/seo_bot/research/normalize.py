"""Data normalization and schema unification for research datasets."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, validator

from .models import Observation


class ObservationSchema(BaseModel):
    """Schema for validating and normalizing observations."""
    value: str  # Add the field that the validator operates on
    metric: str = ""  # Add metric field
    
    @validator('value', pre=True)
    def normalize_value(cls, v, values):
        """Normalize values based on metric type."""
        metric = values.get('metric', '')
        
        if metric == 'price':
            return cls._normalize_price(v)
        elif metric.startswith('spec.'):
            return cls._normalize_specification(v)
        elif metric == 'release_date':
            return cls._normalize_date(v)
        elif metric.startswith('feature.'):
            return cls._normalize_feature(v)
        
        return v
    
    @staticmethod
    def _normalize_price(value: Any) -> float:
        """Normalize price values to standard format."""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove currency symbols and formatting
            cleaned = re.sub(r'[^\d.,]', '', value)
            
            # Handle different decimal separators
            if ',' in cleaned and '.' in cleaned:
                # Assume last separator is decimal
                if cleaned.rindex(',') > cleaned.rindex('.'):
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Check if comma is likely decimal separator
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        
        return 0.0
    
    @staticmethod
    def _normalize_specification(value: Any) -> str:
        """Normalize specification values."""
        if not isinstance(value, str):
            return str(value)
        
        # Clean up common spec formatting
        value = value.strip()
        
        # Normalize units
        unit_mappings = {
            'gb': 'GB',
            'mb': 'MB',
            'tb': 'TB',
            'ghz': 'GHz',
            'mhz': 'MHz',
            'kg': 'kg',
            'lbs': 'lbs',
            'mm': 'mm',
            'cm': 'cm',
            'inch': 'in',
            '"': 'in'
        }
        
        for old_unit, new_unit in unit_mappings.items():
            value = re.sub(rf'\b{old_unit}\b', new_unit, value, flags=re.IGNORECASE)
        
        return value
    
    @staticmethod
    def _normalize_date(value: Any) -> str:
        """Normalize date values to ISO format."""
        if isinstance(value, datetime):
            return value.isoformat()
        
        if isinstance(value, str):
            # Try to parse various date formats
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # ISO format
                r'(\d{1,2}/\d{1,2}/\d{4})',  # US format
                r'(\d{1,2}-\d{1,2}-\d{4})',  # EU format
                r'(\w+\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, value)
                if match:
                    return match.group(1)
        
        return str(value)
    
    @staticmethod
    def _normalize_feature(value: Any) -> bool:
        """Normalize feature flags to boolean."""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.lower().strip()
            return value in ['true', 'yes', 'enabled', 'on', '1', 'available', 'supported']
        
        return bool(value)


class CurrencyConverter:
    """Simple currency converter with common rates."""
    
    # Static rates for demo - in production, use real-time API
    RATES = {
        'EUR': 1.08,
        'GBP': 1.26,
        'JPY': 0.0067,
        'CAD': 0.74,
        'AUD': 0.65,
        'USD': 1.0
    }
    
    @classmethod
    def to_usd(cls, amount: float, currency: str) -> float:
        """Convert amount to USD."""
        currency = currency.upper()
        if currency in cls.RATES:
            return amount * cls.RATES[currency]
        return amount  # Fallback to original amount


class UnitConverter:
    """Convert between different units of measurement."""
    
    # Conversion factors to base units
    CONVERSIONS = {
        # Storage
        'GB': {'base': 'GB', 'factor': 1.0},
        'MB': {'base': 'GB', 'factor': 0.001},
        'TB': {'base': 'GB', 'factor': 1000.0},
        
        # Weight
        'kg': {'base': 'kg', 'factor': 1.0},
        'lbs': {'base': 'kg', 'factor': 0.453592},
        'g': {'base': 'kg', 'factor': 0.001},
        
        # Length
        'mm': {'base': 'mm', 'factor': 1.0},
        'cm': {'base': 'mm', 'factor': 10.0},
        'in': {'base': 'mm', 'factor': 25.4},
        
        # Frequency
        'GHz': {'base': 'GHz', 'factor': 1.0},
        'MHz': {'base': 'GHz', 'factor': 0.001},
    }
    
    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
        """Convert value between units."""
        if from_unit not in cls.CONVERSIONS or to_unit not in cls.CONVERSIONS:
            return value
        
        from_conv = cls.CONVERSIONS[from_unit]
        to_conv = cls.CONVERSIONS[to_unit]
        
        # Convert to base unit, then to target unit
        if from_conv['base'] == to_conv['base']:
            return value * from_conv['factor'] / to_conv['factor']
        
        return value  # Can't convert between different unit types


class DataNormalizer:
    """Main data normalization coordinator."""
    
    def __init__(self):
        self.currency_converter = CurrencyConverter()
        self.unit_converter = UnitConverter()
    
    def normalize_observations(self, observations: List[Observation]) -> List[Observation]:
        """Normalize a list of observations."""
        normalized = []
        
        for obs in observations:
            try:
                normalized_obs = self._normalize_observation(obs)
                normalized.append(normalized_obs)
            except Exception as e:
                # Log error but continue processing
                import logging
                logging.warning(f"Failed to normalize observation {obs.hash}: {e}")
                normalized.append(obs)  # Keep original if normalization fails
        
        return normalized
    
    def _normalize_observation(self, observation: Observation) -> Observation:
        """Normalize a single observation."""
        # Create a copy to avoid modifying original
        normalized = observation.copy()
        
        # Normalize based on metric type
        if observation.metric == 'price':
            normalized = self._normalize_price_observation(normalized)
        elif observation.metric.startswith('spec.'):
            normalized = self._normalize_spec_observation(normalized)
        elif observation.metric == 'release_date':
            normalized = self._normalize_date_observation(normalized)
        
        return normalized
    
    def _normalize_price_observation(self, observation: Observation) -> Observation:
        """Normalize price observations."""
        # Extract currency from value or use default
        currency = 'USD'
        value = observation.value
        
        if isinstance(value, str):
            # Try to extract currency symbol
            currency_patterns = {
                '€': 'EUR',
                '£': 'GBP',
                '¥': 'JPY',
                'C$': 'CAD',
                'A$': 'AUD',
                '$': 'USD'
            }
            
            for symbol, curr in currency_patterns.items():
                if symbol in value:
                    currency = curr
                    break
        
        # Normalize value to float
        numeric_value = ObservationSchema._normalize_price(value)
        
        # Convert to USD
        usd_value = self.currency_converter.to_usd(numeric_value, currency)
        
        observation.value = usd_value
        observation.unit = 'USD'
        
        return observation
    
    def _normalize_spec_observation(self, observation: Observation) -> Observation:
        """Normalize specification observations."""
        value = ObservationSchema._normalize_specification(observation.value)
        
        # Try to extract numeric value and unit
        match = re.search(r'(\d+(?:\.\d+)?)\s*([A-Za-z]+)', value)
        if match:
            numeric_val, unit = match.groups()
            
            # Store normalized format
            observation.value = f"{numeric_val} {unit}"
            observation.unit = unit
        else:
            observation.value = value
        
        return observation
    
    def _normalize_date_observation(self, observation: Observation) -> Observation:
        """Normalize date observations."""
        normalized_date = ObservationSchema._normalize_date(observation.value)
        observation.value = normalized_date
        return observation
    
    def aggregate_by_entity(self, observations: List[Observation]) -> Dict[str, Dict[str, Any]]:
        """Aggregate observations by entity for analysis."""
        entity_data = {}
        
        for obs in observations:
            if obs.entity_id not in entity_data:
                entity_data[obs.entity_id] = {
                    'metrics': {},
                    'first_seen': obs.observed_at,
                    'last_seen': obs.observed_at
                }
            
            # Update timing
            entity_data[obs.entity_id]['first_seen'] = min(
                entity_data[obs.entity_id]['first_seen'], 
                obs.observed_at
            )
            entity_data[obs.entity_id]['last_seen'] = max(
                entity_data[obs.entity_id]['last_seen'], 
                obs.observed_at
            )
            
            # Store metric
            if obs.metric not in entity_data[obs.entity_id]['metrics']:
                entity_data[obs.entity_id]['metrics'][obs.metric] = []
            
            entity_data[obs.entity_id]['metrics'][obs.metric].append({
                'value': obs.value,
                'unit': obs.unit,
                'observed_at': obs.observed_at,
                'source_url': obs.source_url
            })
        
        return entity_data
    
    def detect_changes(self, observations: List[Observation], threshold_days: int = 7) -> List[Dict[str, Any]]:
        """Detect significant changes in observations."""
        changes = []
        entity_data = self.aggregate_by_entity(observations)
        
        for entity_id, data in entity_data.items():
            for metric, values in data['metrics'].items():
                if len(values) < 2:
                    continue
                
                # Sort by observation time
                sorted_values = sorted(values, key=lambda x: x['observed_at'])
                
                # Check for recent changes
                recent = [v for v in sorted_values 
                         if (datetime.now() - v['observed_at']).days <= threshold_days]
                
                if len(recent) >= 2:
                    # Compare latest vs previous
                    latest = recent[-1]
                    previous = recent[-2]
                    
                    if latest['value'] != previous['value']:
                        changes.append({
                            'entity_id': entity_id,
                            'metric': metric,
                            'old_value': previous['value'],
                            'new_value': latest['value'],
                            'change_detected_at': latest['observed_at'],
                            'source_url': latest['source_url']
                        })
        
        return changes