@echo off
REM Windows batch script for running tests
echo Running Arizona U12 Soccer Rankings Tests...
echo.

echo Installing test dependencies...
python -m pip install pytest pytest-cov pandas pyarrow

echo.
echo Running tests...
python -m pytest tests/test_rankings.py -v

echo.
echo Running tests with coverage...
python -m pytest tests/test_rankings.py --cov=rank_core --cov-report=term-missing

echo.
echo Tests complete!
pause
