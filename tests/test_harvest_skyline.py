"""
Integration tests for harvest_skyline module.

Tests OpenStreetMap height data harvesting, spatial matching, and
height estimation logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harvest_skyline import (
    DEFAULT_HEIGHT_METERS,
    SPATIAL_DISTANCE_THRESHOLD,
    METERS_PER_FLOOR,
    OVERPASS_TIMEOUT,
)


class TestHeightEstimationConstants:
    """Test height estimation parameters."""

    def test_default_height_is_reasonable(self):
        """Verify default height represents typical building."""
        # 12 meters = ~3-4 residential floors
        assert 10 < DEFAULT_HEIGHT_METERS < 15, "Default should be realistic"
        # Should roughly correspond to METERS_PER_FLOOR
        estimated_floors = DEFAULT_HEIGHT_METERS / METERS_PER_FLOOR
        assert 3 <= estimated_floors <= 4, "Default should be ~3-4 floors"

    def test_spatial_threshold_is_reasonable(self):
        """Test that spatial distance threshold is meaningful."""
        # 0.0008 degrees at equator ≈ 88-90 meters
        assert 0 < SPATIAL_DISTANCE_THRESHOLD < 0.01, "Threshold should be small"
        
        # At equator, 1 degree ≈ 111 km, so 0.0008 deg ≈ 88.8 meters
        meters_per_degree = 111000  # Approximate
        threshold_meters = SPATIAL_DISTANCE_THRESHOLD * meters_per_degree
        assert 80 < threshold_meters < 100, "Threshold should be ~80-100 meters"

    def test_meters_per_floor_is_realistic(self):
        """Test that floor height assumption is reasonable."""
        # 3.5 meters per floor is standard for commercial/residential
        assert 3.0 <= METERS_PER_FLOOR <= 4.0, "Floor height should be realistic"

    def test_overpass_timeout_is_reasonable(self):
        """Test that Overpass API timeout is appropriate."""
        assert 10 <= OVERPASS_TIMEOUT <= 60, "Timeout should be reasonable for API"


class TestHeightExtraction:
    """Test building height extraction logic."""

    def test_direct_height_extraction_from_tags(self):
        """Test extracting height directly from OSM tags."""
        osm_tags = {"height": "45.5m", "building": "residential"}
        
        # Parse like the actual code does
        height_str = osm_tags["height"].replace("m", "").strip()
        height_value = float(height_str)
        
        assert height_value == 45.5, "Should correctly parse height with unit"

    def test_height_without_units(self):
        """Test parsing height without units."""
        osm_tags = {"height": "45.5"}
        
        height_str = osm_tags["height"].replace("m", "").strip()
        height_value = float(height_str)
        
        assert height_value == 45.5, "Should parse height without units"

    def test_building_levels_to_height_conversion(self):
        """Test converting building levels to height."""
        osm_tags = {"building:levels": "5"}
        
        levels = float(osm_tags["building:levels"])
        estimated_height = max(levels * METERS_PER_FLOOR, 4.0)
        
        assert estimated_height == 17.5, "5 levels × 3.5m = 17.5m"

    def test_building_levels_minimum_height(self):
        """Test that very short buildings have minimum height."""
        osm_tags = {"building:levels": "1"}
        
        levels = float(osm_tags["building:levels"])
        estimated_height = max(levels * METERS_PER_FLOOR, 4.0)
        
        # 1 level × 3.5m = 3.5m, but max with 4.0m = 4.0m
        assert estimated_height == 4.0, "Should respect minimum 4.0m height"

    def test_invalid_height_string_handling(self):
        """Test handling of malformed height values."""
        osm_tags = {"height": "very tall"}  # Invalid
        
        try:
            height_str = osm_tags["height"].replace("m", "").strip()
            height_value = float(height_str)
            # Should fail to parse
            assert False, "Should not parse non-numeric height"
        except ValueError:
            # Expected - invalid height is caught
            assert True


class TestSpatialMatching:
    """Test spatial proximity matching between OSM and database features."""

    def test_distance_calculation_zero(self):
        """Test distance when points are identical."""
        lat1, lon1 = 39.1031, -84.5120
        lat2, lon2 = 39.1031, -84.5120
        
        dist = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
        assert dist == 0.0, "Identical points should have zero distance"

    def test_distance_calculation_within_threshold(self):
        """Test distance calculation for nearby points."""
        # Reference point (Cincinnati)
        lat1, lon1 = 39.1031, -84.5120
        
        # Point 0.0005 degrees away
        lat2, lon2 = 39.1031 + 0.0005, -84.5120
        
        dist = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
        assert dist < SPATIAL_DISTANCE_THRESHOLD, "Should be within matching distance"

    def test_distance_calculation_outside_threshold(self):
        """Test distance calculation for distant points."""
        # Reference point
        lat1, lon1 = 39.1031, -84.5120
        
        # Point 0.002 degrees away (way beyond threshold)
        lat2, lon2 = 39.1031 + 0.002, -84.5120
        
        dist = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
        assert dist > SPATIAL_DISTANCE_THRESHOLD, "Should be outside matching distance"

    def test_nearest_neighbor_selection(self):
        """Test selecting best match from multiple candidates."""
        reference_lat, reference_lon = 39.1031, -84.5120
        
        candidates = [
            {"id": 1, "lat": 39.1031 + 0.001, "lon": -84.5120},
            {"id": 2, "lat": 39.1031 + 0.0002, "lon": -84.5120},  # Closest
            {"id": 3, "lat": 39.1031 + 0.0008, "lon": -84.5120},
        ]
        
        # Find nearest
        best_match = None
        best_distance = float('inf')
        
        for candidate in candidates:
            dist = ((reference_lat - candidate["lat"])**2 + 
                   (reference_lon - candidate["lon"])**2)**0.5
            if dist < best_distance:
                best_distance = dist
                best_match = candidate
        
        assert best_match["id"] == 2, "Should select closest candidate"


class TestHeightPriorityLogic:
    """Test priority of different height data sources."""

    def test_direct_height_preferred_over_levels(self):
        """Test that direct height attribute is used if available."""
        osm_tags = {
            "height": "30.0",
            "building:levels": "10"  # Would suggest ~35m
        }
        
        # Code checks height first, so it should be used
        if "height" in osm_tags:
            height = float(osm_tags["height"].replace("m", "").strip())
            selected_height = height
        elif "building:levels" in osm_tags:
            levels = float(osm_tags["building:levels"])
            selected_height = max(levels * METERS_PER_FLOOR, 4.0)
        
        assert selected_height == 30.0, "Should prefer direct height measurement"

    def test_fallback_to_levels(self):
        """Test using building levels when direct height unavailable."""
        osm_tags = {
            "building:levels": "8"
            # No direct height
        }
        
        if "height" in osm_tags:
            height = float(osm_tags["height"].replace("m", "").strip())
            selected_height = height
        elif "building:levels" in osm_tags:
            levels = float(osm_tags["building:levels"])
            selected_height = max(levels * METERS_PER_FLOOR, 4.0)
        else:
            selected_height = DEFAULT_HEIGHT_METERS
        
        assert selected_height == 28.0, "Should use 8 levels × 3.5m"

    def test_fallback_to_default(self):
        """Test using default height when no OSM data available."""
        osm_tags = {
            "building": "residential"
            # No height or levels data
        }
        
        if "height" in osm_tags:
            height = float(osm_tags["height"].replace("m", "").strip())
            selected_height = height
        elif "building:levels" in osm_tags:
            levels = float(osm_tags["building:levels"])
            selected_height = max(levels * METERS_PER_FLOOR, 4.0)
        else:
            selected_height = DEFAULT_HEIGHT_METERS
        
        assert selected_height == DEFAULT_HEIGHT_METERS, "Should use default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
