"""
Unit tests for Division Registry System

Tests all functions in src/utils/division_registry.py to ensure
proper loading, validation, and error handling.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
sys.path.append('.')

from src.utils.division_registry import (
    load_divisions,
    get_division,
    list_divisions,
    list_active_divisions,
    get_gotsport_url,
    get_master_list_path,
    get_canonical_division_name,
    get_rankings_output_path,
    is_division_active,
    get_division_metadata,
    get_all_active_metadata,
    validate_division_key
)

# Sample test data
SAMPLE_DIVISIONS = {
    "az_boys_u11": {
        "age": 11,
        "gender": "m",
        "state": "AZ",
        "url": "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ",
        "active": True
    },
    "az_boys_u12": {
        "age": 12,
        "gender": "m",
        "state": "AZ",
        "url": "https://rankings.gotsport.com/?team_country=USA&age=12&gender=m&state=AZ",
        "active": True
    },
    "az_girls_u15": {
        "age": 15,
        "gender": "f",
        "state": "AZ",
        "url": "https://rankings.gotsport.com/?team_country=USA&age=15&gender=f&state=AZ",
        "active": False
    }
}

class TestDivisionRegistry:
    """Test cases for division registry functions."""
    
    def test_load_divisions_success(self):
        """Test successful loading of divisions."""
        with patch('src.utils.division_registry.DIVISION_REGISTRY_PATH') as mock_path:
            mock_path.exists.return_value = True
            with patch('builtins.open', mock_open(read_data=json.dumps(SAMPLE_DIVISIONS))):
                divisions = load_divisions()
                assert isinstance(divisions, dict)
                assert "az_boys_u11" in divisions
                assert "az_boys_u12" in divisions
                assert "az_girls_u15" in divisions
    
    def test_load_divisions_file_not_found(self):
        """Test FileNotFoundError when registry file doesn't exist."""
        with patch('src.utils.division_registry.DIVISION_REGISTRY_PATH', Path('nonexistent.json')):
            with pytest.raises(FileNotFoundError):
                load_divisions()
    
    def test_load_divisions_invalid_json(self):
        """Test JSONDecodeError when registry file is malformed."""
        with patch('src.utils.division_registry.DIVISION_REGISTRY_PATH') as mock_path:
            mock_path.exists.return_value = True
            with patch('builtins.open', mock_open(read_data="invalid json")):
                with pytest.raises(json.JSONDecodeError):
                    load_divisions()
    
    def test_load_divisions_missing_fields(self):
        """Test ValueError when division configs are missing required fields."""
        invalid_divisions = {
            "az_boys_u11": {
                "age": 11,
                "gender": "m"
                # Missing: state, url, active
            }
        }
        with patch('src.utils.division_registry.DIVISION_REGISTRY_PATH') as mock_path:
            mock_path.exists.return_value = True
            with patch('builtins.open', mock_open(read_data=json.dumps(invalid_divisions))):
                with pytest.raises(ValueError, match="missing required fields"):
                    load_divisions()
    
    def test_get_division_success(self):
        """Test successful retrieval of division config."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            config = get_division("az_boys_u11")
            assert config["age"] == 11
            assert config["gender"] == "m"
            assert config["state"] == "AZ"
            assert config["active"] is True
    
    def test_get_division_not_found(self):
        """Test KeyError when division not found."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            with pytest.raises(KeyError, match="not found in registry"):
                get_division("nonexistent_division")
    
    def test_list_divisions_all(self):
        """Test listing all divisions."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            divisions = list_divisions(active_only=False)
            assert len(divisions) == 3
            assert "az_boys_u11" in divisions
            assert "az_boys_u12" in divisions
            assert "az_girls_u15" in divisions
    
    def test_list_divisions_active_only(self):
        """Test listing only active divisions."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            active_divisions = list_divisions(active_only=True)
            assert len(active_divisions) == 2
            assert "az_boys_u11" in active_divisions
            assert "az_boys_u12" in active_divisions
            assert "az_girls_u15" not in active_divisions
    
    def test_list_active_divisions(self):
        """Test list_active_divisions convenience function."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            active_divisions = list_active_divisions()
            assert len(active_divisions) == 2
            assert "az_boys_u11" in active_divisions
            assert "az_girls_u15" not in active_divisions
    
    def test_get_gotsport_url(self):
        """Test GotSport URL retrieval."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            url = get_gotsport_url("az_boys_u11")
            assert url == "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ"
    
    def test_get_master_list_path_boys(self):
        """Test master list path generation for boys division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            path = get_master_list_path("az_boys_u11")
            assert path.as_posix() == "data/bronze/AZ MALE u11 MASTER TEAM LIST.csv"
    
    def test_get_master_list_path_girls(self):
        """Test master list path generation for girls division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_girls_u15"]):
            path = get_master_list_path("az_girls_u15")
            assert path.as_posix() == "data/bronze/AZ FEMALE u15 MASTER TEAM LIST.csv"
    
    def test_get_canonical_division_name_boys(self):
        """Test canonical name generation for boys division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            name = get_canonical_division_name("az_boys_u11")
            assert name == "AZ_Boys_U11"
    
    def test_get_canonical_division_name_girls(self):
        """Test canonical name generation for girls division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_girls_u15"]):
            name = get_canonical_division_name("az_girls_u15")
            assert name == "AZ_Girls_U15"
    
    def test_get_rankings_output_path_boys(self):
        """Test rankings output path generation for boys division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            path = get_rankings_output_path("az_boys_u11")
            assert path.as_posix() == "data/outputs/Rankings_AZ_M_U11_2025_v53e.csv"
    
    def test_get_rankings_output_path_girls(self):
        """Test rankings output path generation for girls division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_girls_u15"]):
            path = get_rankings_output_path("az_girls_u15")
            assert path.as_posix() == "data/outputs/Rankings_AZ_F_U15_2025_v53e.csv"
    
    def test_is_division_active_true(self):
        """Test active status check for active division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            assert is_division_active("az_boys_u11") is True
    
    def test_is_division_active_false(self):
        """Test active status check for inactive division."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_girls_u15"]):
            assert is_division_active("az_girls_u15") is False
    
    def test_get_division_metadata(self):
        """Test metadata retrieval."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            metadata = get_division_metadata("az_boys_u11")
            assert metadata["age"] == 11
            assert metadata["gender"] == "m"
            assert metadata["state"] == "AZ"
            assert metadata["active"] is True
            # Should be a copy, not reference
            assert metadata is not SAMPLE_DIVISIONS["az_boys_u11"]
    
    def test_get_all_active_metadata(self):
        """Test getting metadata for all active divisions."""
        with patch('src.utils.division_registry.load_divisions', return_value=SAMPLE_DIVISIONS):
            active_metadata = get_all_active_metadata()
            assert len(active_metadata) == 2
            assert "az_boys_u11" in active_metadata
            assert "az_boys_u12" in active_metadata
            assert "az_girls_u15" not in active_metadata
    
    def test_validate_division_key_valid(self):
        """Test validation of valid division key."""
        with patch('src.utils.division_registry.get_division', return_value=SAMPLE_DIVISIONS["az_boys_u11"]):
            assert validate_division_key("az_boys_u11") is True
    
    def test_validate_division_key_invalid(self):
        """Test validation of invalid division key."""
        with patch('src.utils.division_registry.get_division', side_effect=KeyError("not found")):
            assert validate_division_key("nonexistent") is False
    
    def test_validate_division_key_file_not_found(self):
        """Test validation when registry file doesn't exist."""
        with patch('src.utils.division_registry.get_division', side_effect=FileNotFoundError("file not found")):
            assert validate_division_key("az_boys_u11") is False

def test_integration_with_real_file():
    """Integration test with actual divisions.json file."""
    try:
        # Test that the real file loads without errors
        divisions = load_divisions()
        assert isinstance(divisions, dict)
        assert len(divisions) > 0
        
        # Test that active divisions are returned
        active = list_active_divisions()
        assert len(active) > 0
        
        # Test a known division
        if "az_boys_u11" in divisions:
            config = get_division("az_boys_u11")
            assert config["age"] == 11
            assert config["gender"] == "m"
            assert config["state"] == "AZ"
            assert config["active"] is True
            
            # Test path generation
            master_path = get_master_list_path("az_boys_u11")
            assert "AZ MALE u11" in str(master_path)
            
            rankings_path = get_rankings_output_path("az_boys_u11")
            assert "Rankings_AZ_M_U11" in str(rankings_path)
            
    except FileNotFoundError:
        pytest.skip("Real divisions.json file not found - skipping integration test")

if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])
