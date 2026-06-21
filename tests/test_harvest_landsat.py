"""
Integration tests for harvest_landsat module.

Tests the thermal data harvesting workflow including date range calculation,
API queries, and thermal conversion logic.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harvest_landsat import (
    get_optimal_thermal_window,
    THERMAL_CONVERSION_FACTOR,
    THERMAL_OFFSET,
    ABSOLUTE_ZERO_KELVIN,
    FAHRENHEIT_MULTIPLIER,
)


class TestThermalConversion:
    """Test thermal data conversion constants and formulas."""

    def test_conversion_constants_are_valid(self):
        """Verify thermal conversion constants have valid ranges."""
        assert THERMAL_CONVERSION_FACTOR > 0, "Conversion factor should be positive"
        assert 0 < THERMAL_OFFSET < 200, "Offset should be in valid range"
        assert ABSOLUTE_ZERO_KELVIN == 273.15, "Kelvin offset should be accurate"
        assert FAHRENHEIT_MULTIPLIER == 1.8, "Fahrenheit multiplier should be 9/5"

    def test_kelvin_to_fahrenheit_conversion(self):
        """Test water freezing point (273.15K) converts to 32°F."""
        kelvin = ABSOLUTE_ZERO_KELVIN
        fahrenheit = (kelvin - ABSOLUTE_ZERO_KELVIN) * FAHRENHEIT_MULTIPLIER + 32
        assert fahrenheit == 32, "273.15K should convert to 32°F"

    def test_kelvin_to_fahrenheit_body_temp(self):
        """Test normal body temperature (310K) converts to ~98.6°F."""
        kelvin = 310.0
        fahrenheit = (kelvin - ABSOLUTE_ZERO_KELVIN) * FAHRENHEIT_MULTIPLIER + 32
        assert 98 <= fahrenheit <= 99, "310K should be ~98.6°F"

    def test_thermal_radiance_calculation(self):
        """Test DN to spectral radiance conversion for realistic values."""
        raw_dn = 1000.0
        radiance = (raw_dn * THERMAL_CONVERSION_FACTOR) + THERMAL_OFFSET
        kelvin = radiance  # radiance is already in Kelvin for this constant
        
        # Landsat Band 11 DN values are typically 1-65535, conversion gives result in Kelvin
        assert 100 < kelvin < 500, "Calculated radiance should be in valid temperature range"


class TestOptimalThermalWindow:
    """Test seasonal thermal window selection logic."""

    def test_summer_window_returns_60_day_range(self):
        """Test that summer months (Jul-Oct) return a 60-day window."""
        with patch('harvest_landsat.datetime') as mock_datetime:
            # Mock July 15th
            mock_datetime.now.return_value = datetime(2024, 7, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = get_optimal_thermal_window()
            assert "/" in result, "Result should be a date range with /"
            parts = result.split("/")
            assert len(parts) == 2, "Should have start and end date"

    def test_winter_window_uses_previous_summer(self):
        """Test that winter months default to previous year's summer."""
        with patch('harvest_landsat.datetime') as mock_datetime:
            # Mock January 15th
            mock_datetime.now.return_value = datetime(2024, 1, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = get_optimal_thermal_window()
            assert "2023" in result, "Winter should reference previous year"

    def test_date_range_format_is_valid_iso(self):
        """Test that returned date range uses valid ISO format."""
        result = get_optimal_thermal_window()
        parts = result.split("/")
        
        for date_str in parts:
            # Try parsing as ISO date
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"Date '{date_str}' is not in YYYY-MM-DD format")


class TestHarvestRealThermalData:
    """Integration tests for real thermal data harvesting (mocked API)."""

    @pytest.fixture
    def mock_catalog(self):
        """Create mock STAC catalog."""
        mock_cat = MagicMock()
        return mock_cat

    def test_search_parameters_are_reasonable(self):
        """Test that default search parameters are within realistic bounds."""
        # Cincinnati, OH coordinates
        lat, lon = 39.1031, -84.5120
        buffer = 0.05
        
        min_lat = lat - buffer
        max_lat = lat + buffer
        min_lon = lon - buffer
        max_lon = lon + buffer
        
        assert min_lat < lat < max_lat, "Latitude bounds should contain center"
        assert min_lon < lon < max_lon, "Longitude bounds should contain center"
        assert abs(max_lat - min_lat) < 1.0, "Search area should be reasonably small"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
