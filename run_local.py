# run_local.py — local dev launcher
from dotenv import load_dotenv
load_dotenv()

import subprocess, sys
subprocess.run([
    sys.executable, "-m", "streamlit", "run",
    "app/Home.py",
    "--server.port", "8501",
    "--server.address", "localhost"
])