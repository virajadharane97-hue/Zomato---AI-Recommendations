"""Streamlit entry point for Streamlit Cloud deployment.

This file imports the actual Streamlit app from src/ui/streamlit_app.py
after adding the project root to sys.path.

Deployment: streamlit run streamlit_app.py
"""

import sys
from pathlib import Path

# Add project root to Python path so 'src' module can be imported
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import and run the actual Streamlit app
from src.ui.streamlit_app import *  # noqa: F401, F403
