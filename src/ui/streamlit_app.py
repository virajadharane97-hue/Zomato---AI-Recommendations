"""Streamlit web UI for the restaurant recommendation system.

Usage:
    streamlit run src/ui/streamlit_app.py
"""

from __future__ import annotations

import logging
import time

import streamlit as st

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

# ── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Zomato Restaurant Recommender",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Initialize services (cached) ───────────────────────────────────────────

@st.cache_resource(show_spinner="Loading restaurant dataset…")
def _load_services():
    """Load the repository and recommendation service once."""
    from src.data.loader import DatasetLoader
    from src.data.preprocessor import DataPreprocessor
    from src.data.repository import RestaurantRepository
    from src.services.recommendation import RecommendationService

    repo = RestaurantRepository(
        loader=DatasetLoader(),
        preprocessor=DataPreprocessor(),
    )
    repo.get_all()  # trigger lazy load
    service = RecommendationService(repo)
    return repo, service


# ── Custom CSS ──────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown("""
    <style>
    /* Global font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }

    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }

    /* Card styling */
    .recommendation-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        border: 1px solid #e8e8e8;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .recommendation-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }

    .rank-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #e94560 0%, #c23152 100%);
        color: white !important;
        border-radius: 50%;
        font-weight: 700;
        font-size: 16px;
        margin-right: 12px;
    }

    .restaurant-name {
        font-size: 20px;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 8px;
    }

    .cuisine-tag {
        display: inline-block;
        background: #e8f4f8;
        color: #0f3460;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 4px;
    }

    .stat-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        color: #555;
        margin-right: 20px;
    }

    .ai-insight {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
        border-left: 4px solid #5c6bc0;
        border-radius: 0 12px 12px 0;
        padding: 14px 18px;
        margin-top: 12px;
        font-size: 14px;
        color: #333;
        line-height: 1.6;
    }

    .summary-banner {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        color: white;
        padding: 20px 28px;
        border-radius: 16px;
        margin-bottom: 24px;
        font-size: 16px;
        line-height: 1.6;
    }

    .filter-chip {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    .warning-banner {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 12px 16px;
        border-radius: 0 12px 12px 0;
        margin-bottom: 16px;
        font-size: 14px;
        color: #e65100;
    }

    .metadata-bar {
        background: #f5f5f5;
        border-radius: 12px;
        padding: 14px 20px;
        margin-top: 24px;
        font-size: 13px;
        color: #666;
    }

    /* Main title */
    .main-title {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #e94560, #0f3460);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }

    .sub-title {
        font-size: 16px;
        color: #666;
        margin-bottom: 24px;
    }

    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────────────

def _render_sidebar(repo) -> dict | None:
    """Render the sidebar with preference inputs. Returns prefs dict or None."""
    with st.sidebar:
        st.markdown("## 🍽️ Your Preferences")
        st.markdown("---")

        locations = repo.get_locations()
        cuisines = repo.get_cuisines()

        # Location
        st.markdown("#### 📍 Location")
        location = st.selectbox(
            "Select location",
            options=locations,
            index=None,
            placeholder="Choose a location…",
            label_visibility="collapsed",
            key="location_select",
        )

        # Budget
        st.markdown("#### 💰 Budget")
        budget = st.radio(
            "Select budget tier",
            options=["low", "medium", "high"],
            format_func=lambda x: {"low": "💚 Low (₹0–500)", "medium": "💛 Medium (₹501–1500)", "high": "❤️ High (₹1500+)"}[x],
            index=1,
            label_visibility="collapsed",
            key="budget_radio",
        )

        # Cuisine
        st.markdown("#### 🍳 Cuisine")
        cuisine = st.selectbox(
            "Select cuisine",
            options=["Any"] + cuisines,
            index=0,
            label_visibility="collapsed",
            key="cuisine_select",
        )
        cuisine = None if cuisine == "Any" else cuisine

        # Min rating
        st.markdown("#### ⭐ Minimum Rating")
        min_rating = st.slider(
            "Min rating",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.5,
            format="%.1f",
            label_visibility="collapsed",
            key="rating_slider",
        )

        # Additional
        st.markdown("#### 📝 Additional Preferences")
        additional = st.text_input(
            "Additional",
            placeholder="e.g. family-friendly, rooftop, live music…",
            label_visibility="collapsed",
            key="additional_input",
        )
        additional = additional.strip() or None

        st.markdown("---")

        # Submit
        submitted = st.button(
            "🔍 Get Recommendations",
            use_container_width=True,
            type="primary",
            key="submit_btn",
        )

        if submitted and not location:
            st.error("⚠️ Please select a location first.")
            return None

        if submitted and location:
            return {
                "location": location,
                "budget": budget,
                "cuisine": cuisine,
                "min_rating": min_rating,
                "additional": additional,
            }

    return None


# ── Result rendering ────────────────────────────────────────────────────────

def _render_recommendation_card(rec) -> None:
    """Render a single recommendation card using custom HTML."""
    stars = "★" * int(rec.rating) + "☆" * (5 - int(rec.rating))

    # Build cuisine tags
    cuisine_tags = ""
    for c in rec.cuisine.split(", "):
        cuisine_tags += f'<span class="cuisine-tag">{c.strip()}</span>'

    html = f"""
    <div class="recommendation-card">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <span class="rank-badge">{rec.rank}</span>
            <span class="restaurant-name">{rec.name}</span>
        </div>
        <div style="margin-bottom: 10px;">
            {cuisine_tags}
        </div>
        <div style="margin-bottom: 12px;">
            <span class="stat-item">⭐ {stars} ({rec.rating:.1f})</span>
            <span class="stat-item">💰 ₹{rec.estimated_cost} for two</span>
        </div>
        <div class="ai-insight">
            🤖 <strong>AI Insight:</strong> {rec.explanation}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _render_results(response, prefs: dict, elapsed: float) -> None:
    """Render the full recommendation response."""
    # Applied filters
    filter_chips = ""
    filter_chips += f'<span class="filter-chip">📍 {prefs["location"]}</span>'
    filter_chips += f'<span class="filter-chip">💰 {prefs["budget"].title()}</span>'
    if prefs.get("cuisine"):
        filter_chips += f'<span class="filter-chip">🍳 {prefs["cuisine"]}</span>'
    if prefs.get("min_rating", 0) > 0:
        filter_chips += f'<span class="filter-chip">⭐ ≥{prefs["min_rating"]:.1f}</span>'
    if prefs.get("additional"):
        filter_chips += f'<span class="filter-chip">📝 {prefs["additional"]}</span>'

    st.markdown(f"**Applied Filters:** {filter_chips}", unsafe_allow_html=True)
    st.markdown("")

    # Summary banner
    if response.summary:
        st.markdown(
            f'<div class="summary-banner">💡 {response.summary}</div>',
            unsafe_allow_html=True,
        )

    # Empty state
    if not response.recommendations:
        st.warning(
            "🔍 No restaurants matched your criteria. "
            "Try broadening your filters — different location, budget tier, or cuisine."
        )
        return

    # Recommendation cards
    for rec in response.recommendations:
        _render_recommendation_card(rec)

    # Metadata footer
    meta = response.metadata
    meta_parts = [
        f"📊 Candidates: {meta.candidates_considered}",
        f"🤖 Model: {meta.model or 'N/A'}",
        f"⏱️ Time: {elapsed:.1f}s",
    ]

    st.markdown(
        f'<div class="metadata-bar">{" &nbsp;|&nbsp; ".join(meta_parts)}</div>',
        unsafe_allow_html=True,
    )


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    """Main Streamlit application entry point."""
    _inject_css()

    # Load services
    repo, service = _load_services()

    # Header
    st.markdown('<div class="main-title">🍽️ Zomato Restaurant Recommender</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">AI-powered restaurant picks tailored to your taste</div>', unsafe_allow_html=True)

    # Sidebar
    prefs = _render_sidebar(repo)

    # Results area
    if prefs is not None:
        from src.models.preferences import UserPreferences

        preferences = UserPreferences(**prefs)

        with st.spinner("🔄 Generating AI-powered recommendations…"):
            start = time.perf_counter()
            try:
                response = service.recommend(preferences)
                elapsed = time.perf_counter() - start
                _render_results(response, prefs, elapsed)
            except ValueError as exc:
                elapsed = time.perf_counter() - start
                st.error(f"❌ {exc}")
            except Exception as exc:
                elapsed = time.perf_counter() - start
                st.error(f"❌ An unexpected error occurred: {exc}")
    else:
        # Welcome state
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 📍 Choose Location")
            st.markdown("Pick from cities like **Bangalore**, **Mumbai**, **Delhi**, and more.")

        with col2:
            st.markdown("### 💰 Set Budget")
            st.markdown("Select **Low**, **Medium**, or **High** budget range.")

        with col3:
            st.markdown("### 🤖 Get AI Picks")
            st.markdown("Our AI ranks and explains the best restaurants for you.")

        st.markdown("---")
        st.info("👈 Use the sidebar to enter your preferences and click **Get Recommendations**.")


if __name__ == "__main__":
    main()
