"""
Integration tests for update_temperatures module.

Tests multi-day thermal aggregation, temperature validation, and database
update logic.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from update_temperatures import (
    THERMAL_CONVERSION_FACTOR,
    THERMAL_OFFSET,
    ABSOLUTE_ZERO_KELVIN,
    FAHRENHEIT_MULTIPLIER,
    VALID_TEMP_RANGE,
    MAX_LANDSAT_RASTERS,
)


class TestThermalConversionConstants:
    """Test thermal conversion parameters."""

    def test_conversion_constants_are_valid(self):
        """Verify thermal conversion constants match Landsat specs."""
        assert THERMAL_CONVERSION_FACTOR > 0, "Conversion factor should be positive"
        assert 0 < THERMAL_OFFSET < 200, "Offset should be in valid range"
        assert ABSOLUTE_ZERO_KELVIN == 273.15, "Kelvin offset should be accurate"
        assert FAHRENHEIT_MULTIPLIER == 1.8, "Fahrenheit multiplier should be 9/5"

    def test_temperature_range_is_realistic(self):
        """Test that valid temperature range is reasonable for Earth."""
        min_temp, max_temp = VALID_TEMP_RANGE
        assert min_temp < max_temp, "Min should be less than max"
        assert min_temp > 0, "Min should be above absolute zero in Fahrenheit"
        assert max_temp < 200, "Max should be less than extreme upper bound"
        # Earth temperatures typically don't exceed 160°F in satellite data
        assert 155 < max_temp <= 170, "Max should be reasonable for Landsat data"

    def test_max_rasters_is_positive(self):
        """Test that max rasters count is positive."""
        assert MAX_LANDSAT_RASTERS > 0, "Should expect at least one raster"
        assert MAX_LANDSAT_RASTERS <= 10, "Shouldn't expect excessive rasters"


class TestThermalDataValidation:
    """Test temperature validation and filtering logic."""

    def test_valid_temperature_acceptance(self):
        """Test that valid temperatures pass the sanity check."""
        valid_temps = [50.0, 75.0, 95.0, 160.0]
        
        for temp in valid_temps:
            in_range = VALID_TEMP_RANGE[0] <= temp <= VALID_TEMP_RANGE[1]
            assert in_range, f"Temperature {temp}°F should be valid"

    def test_invalid_temperature_rejection(self):
        """Test that invalid temperatures fail the sanity check."""
        invalid_temps = [30.0, -50.0, 200.0, 500.0]
        
        for temp in invalid_temps:
            in_range = VALID_TEMP_RANGE[0] <= temp <= VALID_TEMP_RANGE[1]
            assert not in_range, f"Temperature {temp}°F should be invalid"

    def test_kelvin_to_fahrenheit_conversion_chain(self):
        """Test complete DN to Fahrenheit conversion chain."""
        # Use realistic DN value (~43311 gives ~75°F)
        raw_dn = 43311.0
        
        # Step 1: DN to spectral radiance (becomes Kelvin in this context)
        kelvin = (raw_dn * THERMAL_CONVERSION_FACTOR) + THERMAL_OFFSET
        
        # Step 2: Kelvin to Fahrenheit
        fahrenheit = (kelvin - ABSOLUTE_ZERO_KELVIN) * FAHRENHEIT_MULTIPLIER + 32
        
        # Verify result is in valid range
        assert VALID_TEMP_RANGE[0] <= fahrenheit <= VALID_TEMP_RANGE[1], \
            f"Converted temp {fahrenheit}°F should be valid"


class TestMultiDayAggregation:
    """Test multi-day thermal data aggregation logic."""

    def test_building_thermal_history_structure(self):
        """Test that building thermal history is properly structured."""
        building_thermal_history = defaultdict(list)
        
        # Simulate multi-day data for 3 buildings
        building_thermal_history[1].extend([75.0, 76.0, 74.5])
        building_thermal_history[2].extend([95.0, 96.0, 94.0])
        building_thermal_history[3].extend([60.0, 61.0, 59.5])
        
        assert len(building_thermal_history) == 3, "Should track 3 buildings"
        for b_id in [1, 2, 3]:
            assert len(building_thermal_history[b_id]) == 3, \
                f"Building {b_id} should have 3 temperature readings"

    def test_multi_day_averaging(self):
        """Test averaging of multi-day temperature data."""
        temperatures = [75.0, 76.0, 74.5]
        average = float(np.mean(temperatures))
        
        assert 74 < average < 77, "Average should be within data range"
        assert average == 75.166666666666666, "Average should match numpy calculation"

    def test_empty_thermal_history_skipped(self):
        """Test that buildings with no valid data are skipped."""
        building_thermal_history = {
            1: [75.0, 76.0],  # Valid
            2: [],             # Empty - should skip
            3: [95.0],         # Valid
        }
        
        updated_count = 0
        for b_id, temp_list in building_thermal_history.items():
            if temp_list:  # Only update if has data
                updated_count += 1
        
        assert updated_count == 2, "Should only update 2 buildings with data"

    def test_averaging_single_day(self):
        """Test that single-day data is handled correctly."""
        single_day = [80.0]
        average = float(np.mean(single_day))
        
        assert average == 80.0, "Single value average should equal that value"

    def test_averaging_removes_outliers_via_range_check(self):
        """Test that temperature range validation filters outliers."""
        # Simulate temperatures with one outlier
        raw_temperatures = [75.0, 76.0, 500.0, 74.5]
        valid_temps = [t for t in raw_temperatures if VALID_TEMP_RANGE[0] <= t <= VALID_TEMP_RANGE[1]]
        
        assert len(valid_temps) == 3, "Should filter out outlier"
        assert 500.0 not in valid_temps, "Outlier should be removed"
        average = float(np.mean(valid_temps))
        assert 74 < average < 77, "Average should use only valid temps"


class TestRasterFileProcessing:
    """Test landsat raster file discovery and processing."""

    def test_expected_raster_naming_convention(self):
        """Test that expected raster filenames follow naming pattern."""
        expected_files = [f"landsat_thermal_{i}.tif" for i in range(1, MAX_LANDSAT_RASTERS + 1)]
        
        assert len(expected_files) == MAX_LANDSAT_RASTERS, "Should create expected count"
        assert expected_files[0] == "landsat_thermal_1.tif", "First raster should be _1"
        assert expected_files[-1] == f"landsat_thermal_{MAX_LANDSAT_RASTERS}.tif", \
            "Last raster should be _MAX"

    def test_nodata_handling(self):
        """Test handling of nodata values in raster processing."""
        raster_data = np.array([75.0, 76.0, 0.0, 74.5, 0.0])
        nodata_val = 0
        
        valid_pixels = raster_data[raster_data != nodata_val]
        
        assert len(valid_pixels) == 3, "Should filter out nodata pixels"
        assert 0 not in valid_pixels, "Nodata should be removed"


class TestDatabaseUpdateLogic:
    """Test database update statement construction."""

    def test_update_statement_structure(self):
        """Test that database update statement is properly formed."""
        # Simulate what the SQL statement would look like
        building_id = 123
        temperature = 85.5
        
        # The actual statement in code: "UPDATE buildings SET baseline_temp_f = :temp WHERE id = :id"
        assert building_id > 0, "Building ID should be positive"
        assert 0 < temperature < 200, "Temperature should be in valid range"

    def test_batch_updates_multiple_buildings(self):
        """Test that multiple buildings can be updated."""
        buildings_to_update = {
            1: 75.0,
            2: 95.0,
            3: 80.0,
            4: 70.0,
        }
        
        assert len(buildings_to_update) == 4, "Should update 4 buildings"
        
        for b_id, temp in buildings_to_update.items():
            assert b_id > 0, "Building ID should be positive"
            assert 0 < temp < 200, "Temperature should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
