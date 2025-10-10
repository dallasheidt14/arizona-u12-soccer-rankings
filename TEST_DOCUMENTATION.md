# Test Suite Documentation

## Overview

The Arizona U12 Soccer Rankings System includes a comprehensive test suite that validates the mathematical correctness of the ranking algorithms and ensures robust handling of edge cases.

## Test Structure

```
tests/
├── fixtures/                    # Test data files
│   ├── toy_games_small.csv     # 2 teams, ≤10 games (penalty testing)
│   ├── toy_games_edge_10_vs_11.csv  # Edge case: 10 vs 11 games
│   ├── toy_games_outliers.csv  # Outlier handling (14-0 blowout)
│   └── toy_master.csv          # Master team list for fixtures
├── conftest.py                 # Pytest configuration and fixtures
└── test_rankings.py           # Main test suite
```

## Test Categories

### 1. Recent Game Weighting Tests
- **`test_recent_weight_no_shrink_for_leq10`**: Verifies teams with ≤10 games don't get recency weighting
- **`test_recent_weight_applies_at_11`**: Confirms 70/30 weighting applies for teams with >10 games

### 2. Mathematical Correctness Tests
- **`test_defense_transform_is_monotone`**: Ensures defense transformation is monotone decreasing
- **`test_power_score_normalization`**: Validates all components are normalized to [0,1] range
- **`test_outlier_capped_by_robust_minmax`**: Tests robust handling of extreme scores

### 3. Strength of Schedule Tests
- **`test_sos_uses_recency`**: Verifies SOS calculation uses recency weighting
- **`test_opponent_strength_calculation`**: Validates opponent strength computation

### 4. Game Count Penalty Tests
- **`test_game_count_penalties`**: Ensures correct penalty application based on game count

### 5. Enhanced History Tests
- **`test_histories_recency_weights_sum_to_1`**: Confirms recency weights sum to 1.0 per team

## Test Data Design

### Toy Games Small (≤10 games)
- **Purpose**: Test penalty application for teams with few games
- **Teams**: Alpha, Bravo
- **Games**: 4 total games
- **Expected**: No recency weighting, penalty applied

### Toy Games Edge (10 vs 11 games)
- **Purpose**: Test boundary between no weighting and 70/30 weighting
- **Teams**: T10 (10 games), T11 (11 games)
- **Expected**: T10 gets no weighting, T11 gets 70/30 weighting

### Toy Games Outliers (Extreme scores)
- **Purpose**: Test robust min-max normalization
- **Teams**: OutA, OutB
- **Games**: Includes 14-0 blowout
- **Expected**: Proper handling without NaN/inf values

## Running Tests

### Command Line
```bash
# Run all tests
python -m pytest tests/test_rankings.py -v

# Run with coverage
python -m pytest tests/test_rankings.py --cov=rank_core --cov-report=term-missing

# Run specific test
python -m pytest tests/test_rankings.py::test_recent_weight_applies_at_11 -v
```

### Windows Batch Script
```cmd
run_tests.bat
```

### Makefile (Unix/Linux)
```bash
make setup    # Install dependencies
make test     # Run tests
make cov      # Run with coverage
```

## Test Philosophy

### Property-Based Testing
Instead of asserting exact values, tests verify mathematical properties:
- ✅ Normalization ranges [0,1]
- ✅ Monotonicity relationships
- ✅ Weight conservation (sums to 1.0)
- ✅ Penalty thresholds

### Edge Case Coverage
- Teams with very few games
- Teams at the 10-game boundary
- Extreme score differentials
- Missing/null data handling

### Deterministic Fixtures
All test data is deterministic and small, ensuring:
- Fast test execution
- Reproducible results
- Easy debugging

## Coverage Report

Current coverage: **86%** of core ranking functions

**Covered Functions:**
- `_robust_minmax()`: Robust normalization
- `calculate_weighted_stats()`: Team statistics with recency weighting
- `calculate_sos()`: Strength of Schedule calculation
- `calculate_power_scores()`: Final power score computation
- `enrich_game_histories_with_opponent_strength()`: Enhanced game histories

**Missing Coverage:**
- Error handling paths
- Edge case branches
- Logging functions

## Continuous Integration

The test suite runs automatically on:
- Every push to main/master branches
- Every pull request
- Via GitHub Actions workflow (`.github/workflows/ci.yml`)

## Adding New Tests

When adding new functionality:

1. **Create test fixtures** in `tests/fixtures/` if needed
2. **Add test functions** in `tests/test_rankings.py`
3. **Follow naming convention**: `test_<functionality>_<expected_behavior>`
4. **Use property-based assertions** rather than exact values
5. **Test edge cases** and error conditions
6. **Update this documentation**

## Test Maintenance

- **Keep fixtures small** and deterministic
- **Update tests** when algorithm changes
- **Monitor coverage** and add tests for uncovered code
- **Review test failures** carefully - they often indicate real bugs
