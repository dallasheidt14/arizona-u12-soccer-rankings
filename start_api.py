import os
import subprocess
import sys

# Ensure we're in the correct directory
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

print(f"Starting FastAPI server from: {os.getcwd()}")
subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])
