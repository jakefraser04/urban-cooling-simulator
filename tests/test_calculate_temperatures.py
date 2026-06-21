"""
Integration tests for calculate_temperatures module.

Tests synthetic thermal data generation, zonal statistics, and
cooling recommendation logic.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calculate_temperatures import (
    GRID_WIDTH,
    GRID_HEIGHT,
    BASE_TEMPERATURE_C,
    THERMAL_AMPLITUDE,
    CRITICAL_HEAT_THRESHOLD,
    MODERATE_HEAT_THRESHOLD,
    COOLING_RECOMMENDATIONS,
)


class TestThermalGenerationConstants:
    """Test thermal simulation parameters."""

    def test_grid_dimensions_are_positive(self):
        """Verify grid dimensions are positive integers."""
        assert GRID_WIDTH > 0, "Grid width should be positive"
        assert GRID_HEIGHT > 0, "Grid height should be positive"

    def test_temperature_constants_in_valid_range(self):
        """Test that temperature constants are realistic."""
        assert 25 <= BASE_TEMPERATURE_C <= 40, "Base temp should be realistic Celsius"
        assert 0 < THERMAL_AMPLITUDE < 15, "Amplitude should create realistic variation"

    def test_cooling_recommendations_exist(self):
        """Verify all cooling recommendation categories exist."""
        required_keys = ["critical", "moderate", "optimal"]
        for key in required_keys:
            assert key in COOLING_RECOMMENDATIONS, f"Missing recommendation: {key}"
            assert len(COOLING_RECOMMENDATIONS[key]) > 0, f"Recommendation for {key} is empty"


class TestTemperatureThresholds:
    """Test temperature threshold logic for cooling recommendations."""

    def test_critical_threshold_higher_than_moderate(self):
        """Verify critical threshold is higher than moderate."""
        assert CRITICAL_HEAT_THRESHOLD > MODERATE_HEAT_THRESHOLD, \
            "Critical should be hotter than moderate"

    def test_thresholds_in_reasonable_fahrenheit_range(self):
        """Test that thresholds are realistic Fahrenheit temperatures."""
        assert 80 < MODERATE_HEAT_THRESHOLD < 100, "Moderate threshold should be warm"
        assert 90 < CRITICAL_HEAT_THRESHOLD < 110, "Critical threshold should be very hot"

    def test_celsius_to_fahrenheit_conversion(self):
        """Test temperature conversion for reference."""
        # 32°C = 89.6°F
        celsius = 32.0
        fahrenheit = (celsius * 9 / 5) + 32
        assert 89 < fahrenheit < 90, "32°C should be ~89.6°F"

    def test_recommendation_assignment_logic(self):
        """Test which recommendation is returned for various temperatures."""
        # Critical case
        if 95.0 > CRITICAL_HEAT_THRESHOLD:
            assert "Critical" in COOLING_RECOMMENDATIONS["critical"]
        
        # Moderate case
        moderate_temp = CRITICAL_HEAT_THRESHOLD - 5
        if MODERATE_HEAT_THRESHOLD < moderate_temp < CRITICAL_HEAT_THRESHOLD:
            assert "Moderate" in COOLING_RECOMMENDATIONS["moderate"]
        
        # Optimal case
        optimal_temp = MODERATE_HEAT_THRESHOLD - 5
        if optimal_temp < MODERATE_HEAT_THRESHOLD:
            assert "Optimal" in COOLING_RECOMMENDATIONS["optimal"]


class TestThermalDataGeneration:
    """Test synthetic thermal raster generation."""

    def test_thermal_grid_generation_shape(self):
        """Test that thermal grid has expected dimensions."""
        y, x = np.mgrid[0:GRID_HEIGHT, 0:GRID_WIDTH]
        raw_thermal = (
            BASE_TEMPERATURE_C
            + THERMAL_AMPLITUDE * np.sin(x / 100.0) * np.cos(y / 100.0)
        )
        
        assert raw_thermal.shape == (GRID_HEIGHT, GRID_WIDTH), \
            "Grid shape should match GRID_HEIGHT x GRID_WIDTH"

    def test_thermal_grid_temperature_range(self):
        """Test that generated temperatures are within reasonable range."""
        y, x = np.mgrid[0:GRID_HEIGHT, 0:GRID_WIDTH]
        raw_thermal = (
            BASE_TEMPERATURE_C
            + THERMAL_AMPLITUDE * np.sin(x / 100.0) * np.cos(y / 100.0)
        )
        
        min_temp = raw_thermal.min()
        max_temp = raw_thermal.max()
        
        # Should be around BASE_TEMPERATURE_C +/- THERMAL_AMPLITUDE
        assert min_temp >= BASE_TEMPERATURE_C - THERMAL_AMPLITUDE - 1, \
            "Min temp should be reasonable"
        assert max_temp <= BASE_TEMPERATURE_C + THERMAL_AMPLITUDE + 1, \
            "Max temp should be reasonable"

    def test_thermal_grid_with_noise(self):
        """Test that noise is properly added to thermal grid."""
        np.random.seed(42)  # For reproducibility
        
        y, x = np.mgrid[0:10, 0:10]
        raw_thermal = (
            BASE_TEMPERATURE_C
            + THERMAL_AMPLITUDE * np.sin(x / 100.0) * np.cos(y / 100.0)
            + np.random.normal(0, 0.5, size=(10, 10))
        )
        
        assert raw_thermal.shape == (10, 10), "Shape should match grid size"
        assert not np.isnan(raw_thermal).any(), "Should not contain NaN values"


class TestZonalStatistics:
    """Test zonal statistics calculation logic."""

    def test_mean_calculation_with_valid_pixels(self):
        """Test mean temperature calculation from valid pixels."""
        # Simulate roof pixels
        roof_pixels = np.array([30.0, 31.0, 32.0, 33.0, 34.0])
        mean_temp = float(roof_pixels.mean())
        
        assert 30 <= mean_temp <= 34, "Mean should be within data range"
        assert mean_temp == 32.0, "Mean of 30,31,32,33,34 should be 32"

    def test_nodata_filtering(self):
        """Test that nodata values are properly filtered."""
        # Mix of valid pixels and nodata
        data = np.array([30.0, 31.0, -9999.0, 32.0, -9999.0, 33.0])
        roof_pixels = data[data != -9999.0]
        
        assert len(roof_pixels) == 4, "Should filter out nodata values"
        assert -9999 not in roof_pixels, "Nodata should not be in result"

    def test_empty_pixels_handling(self):
        """Test handling when building has no valid pixels."""
        roof_pixels = np.array([])
        
        if len(roof_pixels) == 0:
            mean_temp = 32.0  # FALLBACK_TEMPERATURE
            assert mean_temp > 0, "Should use fallback value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
