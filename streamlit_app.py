"""Minimal Streamlit entry point for debugging deployment issues."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

# Show that the app is loading
st.title("🍽️ Zomato AI Restaurant Recommender")
st.info("⏳ App is initializing... Please wait.")

# Check environment
import os
groq_key = os.getenv("GROQ_API_KEY", "")

st.sidebar.header("Environment Check")
st.sidebar.success(f"✅ Python path configured")
st.sidebar.success(f"✅ Streamlit loaded")
if groq_key:
    st.sidebar.success(f"✅ GROQ_API_KEY found (length: {len(groq_key)})")
else:
    st.sidebar.error("❌ GROQ_API_KEY not found")
    st.warning("""
    **Missing GROQ_API_KEY!**
    
    Add it to Streamlit Secrets:
    ```toml
    GROQ_API_KEY = "your_key_here"
    ```
    """)

# Now try to import the actual app
try:
    with st.spinner("Loading restaurant dataset and AI models..."):
        # Import the main app module
        from src.ui import streamlit_app as main_app
        
        # Call the main function
        main_app.main()
        
except Exception as e:
    import traceback
    
    st.error(f"## ❌ Error Loading App")
    st.error(f"**{type(e).__name__}:** {str(e)}")
    
    with st.expander("📋 Full Traceback (click to expand)"):
        st.code(traceback.format_exc())
    
    st.markdown("---")
    st.info("""
    **Next Steps:**
    1. Check the deployment logs for details
    2. Verify all dependencies are installed
    3. Ensure GROQ_API_KEY is set in Streamlit Secrets
    """)
