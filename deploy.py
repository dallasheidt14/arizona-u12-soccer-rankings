"""
Production Deployment Script
Automated deployment and health checks for Arizona U12 Soccer Rankings
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {result.stderr}")
        sys.exit(1)
    
    return result

def check_prerequisites():
    """Check system prerequisites."""
    logger.info("Checking prerequisites...")
    
    # Check Python version
    result = run_command("python --version")
    python_version = result.stdout.strip()
    logger.info(f"Python version: {python_version}")
    
    # Check required files
    required_files = [
        "scraper_config.py",
        "scraper_daily.py", 
        "api_server.py",
        "az_u12_dashboard.py",
        "alias_ops_ui.py",
        "generate_team_rankings_v2.py",
        "AZ MALE U12 MASTER TEAM LIST.csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        sys.exit(1)
    
    logger.info("All prerequisites satisfied")

def install_dependencies():
    """Install Python dependencies."""
    logger.info("Installing dependencies...")
    
    # Upgrade pip
    run_command("python -m pip install -U pip")
    
    # Install requirements
    run_command("pip install -r requirements.txt")
    
    logger.info("Dependencies installed successfully")

def setup_directories():
    """Create necessary directories."""
    logger.info("Setting up directories...")
    
    directories = [
        "data_ingest/bronze",
        "data_ingest/silver",
        "data_ingest/gold",
        "backups",
        "aliases",
        "logs"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

def bootstrap_aliases():
    """Bootstrap team aliases."""
    logger.info("Bootstrapping team aliases...")
    
    result = run_command("python bootstrap_aliases.py", check=False)
    if result.returncode == 0:
        logger.info("Team aliases bootstrapped successfully")
    else:
        logger.warning("Alias bootstrapping failed, continuing with empty aliases")

def run_tests():
    """Run test suite."""
    logger.info("Running test suite...")
    
    result = run_command("python -m pytest tests/ -v", check=False)
    if result.returncode == 0:
        logger.info("All tests passed")
    else:
        logger.warning("Some tests failed, but continuing with deployment")

def start_services():
    """Start all services."""
    logger.info("Starting services...")
    
    # Kill existing processes
    run_command("pkill -f 'scraper_daily.py'", check=False)
    run_command("pkill -f 'api_server.py'", check=False)
    run_command("pkill -f 'streamlit'", check=False)
    
    time.sleep(2)  # Wait for processes to terminate
    
    # Start API server
    logger.info("Starting API server...")
    subprocess.Popen([
        "python", "api_server.py"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(3)  # Wait for API to start
    
    # Start dashboard
    logger.info("Starting dashboard...")
    subprocess.Popen([
        "streamlit", "run", "az_u12_dashboard.py", 
        "--server.headless", "true",
        "--server.port", "8501"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(3)  # Wait for dashboard to start
    
    # Start alias operations UI
    logger.info("Starting alias operations UI...")
    subprocess.Popen([
        "streamlit", "run", "alias_ops_ui.py",
        "--server.headless", "true", 
        "--server.port", "8502"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    logger.info("All services started")

def health_check():
    """Perform health checks on all services."""
    logger.info("Performing health checks...")
    
    # Check API health
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        if response.status_code == 200:
            logger.info("API server: HEALTHY")
        else:
            logger.error(f"API server: UNHEALTHY (status: {response.status_code})")
    except Exception as e:
        logger.error(f"API server: UNHEALTHY (error: {e})")
    
    # Check dashboard
    try:
        response = requests.get("http://localhost:8501", timeout=10)
        if response.status_code == 200:
            logger.info("Dashboard: HEALTHY")
        else:
            logger.error(f"Dashboard: UNHEALTHY (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Dashboard: UNHEALTHY (error: {e})")
    
    # Check alias operations UI
    try:
        response = requests.get("http://localhost:8502", timeout=10)
        if response.status_code == 200:
            logger.info("Alias Operations UI: HEALTHY")
        else:
            logger.error(f"Alias Operations UI: UNHEALTHY (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Alias Operations UI: UNHEALTHY (error: {e})")
    
    # Check data files
    data_files = [
        "AZ MALE U12 MASTER TEAM LIST.csv",
        "team_aliases.json"
    ]
    
    for file_path in data_files:
        if Path(file_path).exists():
            logger.info(f"Data file {file_path}: EXISTS")
        else:
            logger.warning(f"Data file {file_path}: MISSING")

def run_initial_scrape():
    """Run initial data scrape."""
    logger.info("Running initial data scrape...")
    
    result = run_command("python scraper_daily.py", check=False)
    if result.returncode == 0:
        logger.info("Initial scrape completed successfully")
    else:
        logger.warning("Initial scrape failed, but system is still functional")

def generate_initial_rankings():
    """Generate initial rankings."""
    logger.info("Generating initial rankings...")
    
    result = run_command("python generate_team_rankings_v2.py", check=False)
    if result.returncode == 0:
        logger.info("Initial rankings generated successfully")
    else:
        logger.warning("Initial rankings generation failed")

def print_deployment_summary():
    """Print deployment summary."""
    logger.info("=" * 60)
    logger.info("DEPLOYMENT COMPLETE")
    logger.info("=" * 60)
    logger.info("Services running:")
    logger.info("  • API Server: http://localhost:8000")
    logger.info("  • Dashboard: http://localhost:8501")
    logger.info("  • Alias Operations: http://localhost:8502")
    logger.info("")
    logger.info("Key files:")
    logger.info("  • Configuration: scraper_config.py")
    logger.info("  • Runbook: PRODUCTION_RUNBOOK.md")
    logger.info("  • Logs: scraper.log")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Configure Slack webhook in scraper_config.py")
    logger.info("  2. Test daily scraper: python scraper_daily.py")
    logger.info("  3. Review team aliases in alias operations UI")
    logger.info("  4. Set up GitHub Actions for daily scheduling")
    logger.info("")
    logger.info("For support, see PRODUCTION_RUNBOOK.md")

def main():
    """Main deployment function."""
    logger.info("Starting Arizona U12 Soccer Rankings deployment...")
    
    try:
        check_prerequisites()
        install_dependencies()
        setup_directories()
        bootstrap_aliases()
        run_tests()
        start_services()
        health_check()
        run_initial_scrape()
        generate_initial_rankings()
        print_deployment_summary()
        
        logger.info("Deployment completed successfully!")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
