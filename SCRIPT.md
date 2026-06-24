# Zomato AI Restaurant Recommendations - Complete Project Guide

## 📋 Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Key Features](#key-features)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**Zomato AI** is an intelligent restaurant recommendation system that uses Groq's LLM (Large Language Model) to provide personalized, AI-curated restaurant recommendations based on user preferences.

### What Makes It Special?
- 🧠 **AI-Powered**: Uses Groq's llama-3.3-70b model for intelligent ranking and explanations
- 📊 **Large Dataset**: 12,157 unique restaurants (deduplicated from 51,717 records)
- 🎨 **Dual Interface**: Both Streamlit web app AND modern React frontend
- ⚡ **Fast**: Groq's inference engine provides sub-second AI responses
- 🌙 **Dark Mode**: Full dark mode support in React frontend
- 📍 **Smart Filtering**: Location, budget, cuisine, rating, and custom preferences

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                         │
├──────────────────────────┬──────────────────────────────────┤
│   Streamlit Web App      │   React Frontend (Vite + TS)     │
│   (src/ui/streamlit)     │   (frontend/)                    │
└──────────┬───────────────┴──────────┬───────────────────────┘
           │                          │
           │                          │ HTTP/API
           ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                           │
│                    (src/api/routes.py)                       │
│                                                              │
│  Endpoints:                                                  │
│  • GET  /api/v1/health                                       │
│  • GET  /api/v1/locations                                    │
│  • GET  /api/v1/cuisines                                     │
│  • POST /api/v1/recommend                                    │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                 RECOMMENDATION ENGINE                        │
│              (src/services/recommendation.py)                │
│                                                              │
│  1. Filter candidates (location, budget, cuisine, rating)   │
│  2. Build AI prompt with context                            │
│  3. Call Groq LLM for ranking & explanations                │
│  4. Parse & validate AI response                            │
│  5. Return top 5 recommendations                            │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│              (src/data/repository.py)                        │
│                                                              │
│  • DatasetLoader: Downloads from Hugging Face               │
│  • DataPreprocessor: Cleans & deduplicates                  │
│  • RestaurantRepository: In-memory data access              │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **Groq SDK**: LLM inference (llama-3.3-70b-versatile)
- **Pandas**: Data manipulation and analysis
- **Datasets**: Hugging Face dataset loading and caching

### Frontend (React)
- **React 18**: UI library
- **Vite**: Fast build tool and dev server
- **TypeScript**: Type-safe JavaScript
- **TailwindCSS v4**: Utility-first CSS framework
- **React Hook Form**: Form management
- **Zod**: Schema validation
- **Lucide React**: Icon library

### Frontend (Streamlit)
- **Streamlit**: Rapid Python web app framework
- **Custom CSS**: Branded styling with Zomato colors

### Infrastructure
- **Hugging Face**: Dataset hosting
- **Streamlit Cloud**: Free deployment platform
- **GitHub**: Version control and CI/CD

---

## 📁 Project Structure

```
zomato-ai-recommendations/
│
├── 📂 src/                          # Backend source code
│   ├── api/                         # FastAPI routes & schemas
│   │   ├── routes.py                # API endpoint definitions
│   │   └── schemas.py               # Pydantic request/response models
│   │
│   ├── data/                        # Data layer
│   │   ├── loader.py                # Hugging Face dataset downloader
│   │   ├── preprocessor.py          # Data cleaning & deduplication
│   │   └── repository.py            # In-memory restaurant database
│   │
│   ├── models/                      # Data models
│   │   ├── preferences.py           # User preference model
│   │   ├── recommendation.py        # Recommendation response model
│   │   └── restaurant.py            # Restaurant entity model
│   │
│   ├── services/                    # Business logic
│   │   ├── recommendation.py        # Main recommendation engine
│   │   ├── llm_client.py            # Groq API client
│   │   ├── prompt_builder.py        # AI prompt construction
│   │   ├── filter.py                # Restaurant filtering logic
│   │   └── validator.py             # Response validation
│   │
│   ├── ui/                          # User interfaces
│   │   ├── streamlit_app.py         # Streamlit web app (433 lines)
│   │   └── cli.py                   # Command-line interface
│   │
│   ├── config.py                    # Application configuration
│   └── main.py                      # FastAPI application entry point
│
├── 📂 frontend/                     # React frontend
│   ├── src/
│   │   ├── components/              # React components
│   │   │   ├── PreferenceForm.tsx   # User preferences form
│   │   │   ├── RecommendationCard.tsx # Restaurant card
│   │   │   ├── ResultsGrid.tsx      # Results display grid
│   │   │   ├── SummaryBanner.tsx    # AI summary display
│   │   │   ├── LoadingSkeleton.tsx  # Loading placeholders
│   │   │   ├── EmptyState.tsx       # Empty state UI
│   │   │   └── FilterBadges.tsx     # Filter indicator chips
│   │   │
│   │   ├── pages/
│   │   │   └── HomePage.tsx         # Main page orchestrator
│   │   │
│   │   ├── lib/
│   │   │   └── api.ts               # Typed API client
│   │   │
│   │   ├── types/
│   │   │   └── api.ts               # TypeScript API types
│   │   │
│   │   ├── App.tsx                  # Root component (header, dark mode)
│   │   ├── main.tsx                 # React entry point
│   │   └── index.css                # Global styles & Tailwind config
│   │
│   ├── public/                      # Static assets
│   ├── vite.config.ts               # Vite configuration
│   ├── tsconfig.json                # TypeScript configuration
│   └── package.json                 # Node.js dependencies
│
├── 📂 tests/                        # Unit tests
│   ├── test_filter.py               # Filter service tests
│   ├── test_preprocessor.py         # Data preprocessing tests
│   └── test_recommendation.py       # Recommendation engine tests
│
├── 📂 data/                         # Dataset cache (gitignored)
│   └── train.parquet                # Cached dataset (~50MB)
│
├── 📂 .streamlit/                   # Streamlit configuration
│   └── config.toml                  # Theme & app settings
│
├── streamlit_app.py                 # Streamlit Cloud entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
│
└── Documentation files:
    ├── architecture.md              # System architecture docs
    ├── implementation-plan.md       # Phase-wise implementation plan
    ├── edge-case.md                 # Edge cases & corner scenarios
    └── context.md                   # Project context & decisions
```

---

## 🔄 How It Works

### User Flow
1. **User opens app** (Streamlit or React)
2. **Enters preferences**:
   - 📍 Location (e.g., "Koramangala", "Indiranagar")
   - 💰 Budget tier (Low ≤₹500, Medium ₹501-1500, High ₹1500+)
   - 🍕 Cuisine (optional, e.g., "Italian", "Chinese")
   - ⭐ Minimum rating (0.0 - 5.0 slider)
   - 💬 Additional preferences (optional text)
3. **Clicks "Get Recommendations"**
4. **Backend processes request**:
   - Filters 12,157 restaurants by criteria
   - Selects top 20 candidates
   - Sends to Groq LLM with context
   - LLM ranks & explains top 5
5. **User sees AI-curated results** with:
   - Restaurant name & rank
   - Cuisine type
   - Rating & estimated cost
   - **AI-generated explanation** for why it matches

### AI Prompt Example
```
You are a restaurant recommendation expert. Based on the following 
user preferences and available restaurants, rank the top 5 options 
and explain why each is a good match.

User Preferences:
- Location: Koramangala
- Budget: Medium (₹501-1500)
- Cuisine: Italian
- Min Rating: 4.0
- Additional: outdoor seating, romantic

Available Restaurants: [20 candidates with details...]

Return JSON with rank, name, cuisine, rating, estimated_cost, 
and explanation for each.
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ (for React frontend)
- Groq API key (free at https://console.groq.com/keys)

### 1. Clone Repository
```bash
git clone https://github.com/virajadharane97-hue/Zomato---AI-Recommendations.git
cd Zomato---AI-Recommendations
```

### 2. Setup Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Groq API key
nano .env  # or use any editor
```

**.env file:**
```env
GROQ_API_KEY=gsk_your_actual_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3
```

### 4. Setup React Frontend (Optional)
```bash
cd frontend
npm install
cd ..
```

---

## ▶️ Running the Application

### Option 1: Streamlit Web App (Recommended)
```bash
streamlit run streamlit_app.py
```
Opens at: http://localhost:8501

### Option 2: FastAPI Backend + React Frontend

**Terminal 1 - Start Backend:**
```bash
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```
API at: http://localhost:8000
API Docs: http://localhost:8000/docs

**Terminal 2 - Start React Frontend:**
```bash
cd frontend
npm run dev
```
Opens at: http://localhost:5173

### Option 3: Command Line Interface
```bash
python -m src.ui.cli
```

---

## 🌐 Deployment

### Streamlit Cloud (Free)

1. **Push code to GitHub** (already done)
   ```bash
   git push origin main
   ```

2. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"

3. **Configure App**
   - Repository: `virajadharane97-hue/Zomato---AI-Recommendations`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

4. **Add Secrets**
   - Go to app Settings → Secrets
   - Add:
   ```toml
   GROQ_API_KEY = "your_groq_api_key"
   ```

5. **Deploy!**
   - First deploy: 3-5 minutes (downloading dataset)
   - Subsequent deploys: 1-2 minutes

### Vercel (React Frontend)
```bash
cd frontend
npm install -g vercel
vercel --prod
```

---

## 📡 API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "ok",
  "dataset_loaded": true
}
```

#### 2. Get Locations
```http
GET /locations
```
**Response:**
```json
{
  "locations": ["Bangalore", "Mumbai", "Delhi", ...],
  "count": 93
}
```

#### 3. Get Cuisines
```http
GET /cuisines
```
**Response:**
```json
{
  "cuisines": ["Italian", "Chinese", "Indian", ...],
  "count": 105
}
```

#### 4. Get Recommendations
```http
POST /recommend
Content-Type: application/json

{
  "location": "Koramangala",
  "budget": "medium",
  "cuisine": "Italian",
  "min_rating": 4.0,
  "additional": "romantic, outdoor seating"
}
```
**Response:**
```json
{
  "summary": "Based on your preferences for Italian cuisine...",
  "recommendations": [
    {
      "rank": 1,
      "name": "Little Italy",
      "cuisine": "Italian",
      "rating": 4.5,
      "estimated_cost": 1200,
      "explanation": "Perfect match for romantic Italian dining..."
    },
    // ... 4 more
  ],
  "metadata": {
    "total_candidates": 20,
    "processing_time_ms": 850
  }
}
```

---

## ✨ Key Features

### 🧠 AI-Powered Recommendations
- Uses Groq's llama-3.3-70b model
- Contextual explanations for each recommendation
- Considers multiple factors: location, budget, cuisine, rating, preferences

### 📊 Smart Data Processing
- **Dataset**: 51,717 raw records → 12,157 unique restaurants
- **Deduplication**: Removed 39,560 duplicate entries
- **Caching**: Local parquet cache avoids re-downloading
- **Preprocessing**: Automated cleaning and validation

### 🎨 Dual Frontend Support
- **Streamlit**: Quick deployment, Python-native, great for demos
- **React**: Modern UI, dark mode, better UX, production-ready

### ⚡ Performance
- FastAPI async architecture
- Groq sub-second LLM inference
- In-memory data repository
- Vite HMR for fast development

### 🔒 Security
- API key managed via environment variables
- `.gitignore` prevents secret commits
- GitHub push protection enabled
- No hardcoded credentials

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | `""` | Groq API key (required) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Primary LLM model |
| `GROQ_FALLBACK_MODEL` | `llama-3.1-8b-instant` | Fallback model |
| `GROQ_TEMPERATURE` | `0.3` | LLM creativity (0.0-2.0) |
| `HF_DATASET_NAME` | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset |
| `MAX_CANDIDATES_FOR_LLM` | `20` | Candidates sent to LLM |
| `TOP_K_RECOMMENDATIONS` | `5` | Number of results returned |

### Budget Thresholds
- **Low**: ₹0 - ₹500
- **Medium**: ₹501 - ₹1,500
- **High**: ₹1,501+

---

## 🐛 Troubleshooting

### Streamlit Cloud: Blank Screen
**Problem**: App shows blank screen after deployment

**Solutions**:
1. Check deployment logs (Settings → Logs)
2. Verify GROQ_API_KEY is set in Secrets
3. Ensure `streamlit_app.py` is the main file path
4. Check for import errors in traceback

### ModuleNotFoundError: No module named 'src'
**Problem**: Python can't find the `src` module

**Solution**: Already fixed! The `streamlit_app.py` adds project root to `sys.path`:
```python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
```

### Dataset Download Fails
**Problem**: "Failed to load dataset after 3 retries"

**Solutions**:
1. Check internet connection
2. Hugging Face might be temporarily down
3. Dataset will retry automatically
4. For local: manually download and place in `data/train.parquet`

### Groq API Key Issues
**Problem**: "Invalid API key" or rate limit errors

**Solutions**:
1. Get fresh key from https://console.groq.com/keys
2. Check key format (should start with `gsk_`)
3. Free tier: 10,000 tokens/day limit
4. Add to Streamlit Secrets without quotes

### React Frontend: Dropdowns Empty
**Problem**: Location/cuisine dropdowns show no data

**Solutions**:
1. Ensure backend is running: `http://localhost:8000`
2. Check Vite proxy in `vite.config.ts` uses `127.0.0.1:8000`
3. Open browser console (F12) for errors
4. Hard refresh (Ctrl+Shift+R)

### Dark Mode Not Working
**Problem**: Dark mode toggle doesn't change theme

**Solutions**:
1. Check `@custom-variant dark (&:where(.dark, .dark *));` in `index.css`
2. Clear browser cache
3. Verify `localStorage.getItem('theme')` in browser console

---

## 📊 Project Statistics

- **Total Lines of Code**: ~13,000+
- **Python Files**: 20+
- **TypeScript/React Files**: 15+
- **Test Coverage**: 3 test modules
- **Dataset Size**: 12,157 unique restaurants
- **API Endpoints**: 4
- **Frontend Components**: 8 React components
- **Supported Locations**: 93
- **Supported Cuisines**: 105

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is built for educational and demonstration purposes.

---

## 🔗 Useful Links

- **GitHub Repository**: https://github.com/virajadharane97-hue/Zomato---AI-Recommendations
- **Groq API**: https://console.groq.com/keys
- **Hugging Face Dataset**: https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Streamlit**: https://streamlit.io/
- **React**: https://react.dev/
- **TailwindCSS**: https://tailwindcss.com/

---

## 🎓 Learning Resources

### Understanding the Code
1. **Start with**: `src/data/loader.py` - See how dataset is loaded
2. **Then**: `src/data/preprocessor.py` - Data cleaning logic
3. **Then**: `src/services/recommendation.py` - Core AI recommendation logic
4. **Finally**: `src/ui/streamlit_app.py` or `frontend/src/App.tsx` - UI layer

### Key Design Patterns
- **Repository Pattern**: `RestaurantRepository` abstracts data access
- **Service Layer**: Business logic separated from routes
- **Dependency Injection**: Services injected into routes
- **Caching**: `@st.cache_resource` and local parquet cache
- **Lazy Loading**: Dataset loaded on first access only

---

**Built with ❤️ using AI, FastAPI, React, and Groq**
