"""Streamlit entry point for Streamlit Cloud deployment.

This file imports the actual Streamlit app from src/ui/streamlit_app.py
after adding the project root to sys.path.

Deployment: streamlit run streamlit_app.py
"""

import sys
import traceback
from pathlib import Path

# Add project root to Python path so 'src' module can be imported
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Check for required environment variables
import os
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()

# Verify GROQ_API_KEY is set
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    import streamlit as st
    st.error("""
    ## ⚠️ Missing GROQ_API_KEY
    
    This app requires a Groq API key to function.
    
    **To fix this:**
    1. Get a free API key from: https://console.groq.com/keys
    2. Add it to Streamlit Cloud:
       - Go to your app settings
       - Navigate to **Secrets**
       - Add: `GROQ_API_KEY = \"your_key_here\"`
    3. Redeploy the app
    
    [Get your Groq API key →](https://console.groq.com/keys)
    """)
    st.stop()

# Import and run with comprehensive error handling
try:
    from src.ui.streamlit_app import *  # noqa: F401, F403
except Exception as e:
    import streamlit as st
    st.error("## ❌ Application Error")
    st.error(f"**Error type:** {type(e).__name__}")
    st.error(f"**Message:** {str(e)}")
    st.markdown("---")
    st.markdown("### Full Traceback:")
    st.code(traceback.format_exc())
    st.markdown("---")
    st.info("**Common fixes:**\n"
            "- Check the deployment logs for details\n"
            "- Ensure all dependencies are in requirements.txt\n"
            "- Verify the GROQ_API_KEY is correctly set in Secrets")
