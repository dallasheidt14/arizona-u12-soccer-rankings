# Changelog

All notable changes to the Arizona Soccer Rankings project will be documented in this file.

## [v1.2] - 2025-10-11

### Added
- **Division Registry System** (`data/divisions.json`)
  - Centralized configuration for all divisions
  - Support for active/inactive divisions
  - Metadata: age, gender, state, GotSport URL
  - Boys U10-U14 active, U15-U19 + Girls U15-U19 placeholders
  
- **Registry Helper Module** (`src/utils/division_registry.py`)
  - `load_divisions()`, `get_division()`, `list_active_divisions()`
  - `get_gotsport_url()`, `get_master_list_path()`
  - `get_rankings_output_path()`, `get_canonical_division_name()`
  - Auto-generation of file paths from division keys
  
- **Registry Integration**
  - Scraper uses registry for URL lookup with fallback
  - Rankings script uses registry for master list paths
  - Dashboard auto-discovers divisions from registry (hybrid mode)
  
- **Comprehensive Test Suite** (`tests/test_division_registry.py`)
  - 24 test cases covering all registry functions
  - Error handling and edge case testing
  - Integration tests with real registry file

- **Enhanced Division Utils** (`src/utils/division.py`)
  - Registry integration with backward compatibility
  - Fallback to string parsing when registry unavailable

- **Multi-Division Documentation** (`docs/MULTI_DIVISION_GUIDE.md`)
  - Complete guide for adding new divisions
  - Registry API reference
  - Troubleshooting and best practices

### Changed
- `src/utils/division.py`: Enhanced with registry integration
- `src/scrapers/scraper_multi_division.py`: URL lookup via registry with fallback
- `src/rankings/generate_team_rankings_v53_enhanced_multi.py`: Master list paths via registry
- `src/dashboard/app_v53_multi_division.py`: Hybrid auto-discovery with manual fallback

### Benefits
- **Zero code changes** to add new divisions
- **Single source of truth** for division configuration
- **Scalable** to any age group or gender
- **Backward compatible** with existing scripts
- **Auto-discovery** in dashboard and other components

## [v1.1] - 2025-10-10

### Added
- Complete repository restructuring under `/src/` package layout
- Layered data architecture (`data/bronze`, `data/silver`, `data/gold`, `data/outputs`)
- Modern Python packaging with `pyproject.toml` and `pip install -e .`
- Updated imports to use `from src.utils...` across all modules
- Updated Makefile paths and dashboard configuration
- Unified fallback logic in data loader (new `data/` paths)
- CI/CD compatible structure with clear testing and nightly workflows

### Fixed
- U12 ranking path alignment (`Rankings_AZ_M_U12_2025_v53e.csv`)
- Minor schema inconsistencies and import path issues

### Verified
- All tests passing (`pytest -q tests/`)
- Dashboard launches successfully
- U11 & U12 fully functional (130 & 148 teams respectively)

## [v1.0] - 2025-10-09

### Added
- Initial U11 pipeline implementation
- Multi-division scraper architecture
- V5.3E enhanced ranking algorithm
- Streamlit dashboard with division switching
- Comprehensive test suite
- GitHub Actions CI/CD pipeline
- Makefile automation

### Features
- Boys U10-U14 division support
- Team canonicalization and aliasing
- Strength-adjusted PowerScores
- Connectivity analysis and reporting
- Interactive dashboard with predictions
