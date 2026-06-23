# AI-Powered Restaurant Recommendation System (Zomato Use Case)

## Overview

Build an AI-powered restaurant recommendation service inspired by Zomato. The system intelligently suggests restaurants based on user preferences by combining structured data with a Large Language Model (LLM).

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face:  
  **https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation**
- Extract relevant fields such as:
  - Restaurant name
  - Location
  - Cuisine
  - Cost
  - Rating
  - (and other applicable fields from the dataset)

### 2. User Input

Collect user preferences:

| Preference | Examples |
|------------|----------|
| Location | Delhi, Bangalore |
| Budget | low, medium, high |
| Cuisine | Italian, Chinese |
| Minimum rating | numeric threshold |
| Additional preferences | family-friendly, quick service |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM reason and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants
- Provide explanations (why each recommendation fits)
- Optionally summarize choices

### 5. Output Display

Present top recommendations in a user-friendly format:

| Field | Description |
|-------|-------------|
| Restaurant Name | Name of the recommended restaurant |
| Cuisine | Type of cuisine offered |
| Rating | Restaurant rating |
| Estimated Cost | Approximate cost for dining |
| AI-generated explanation | Why this restaurant was recommended |

## Data Source

- **Dataset:** Zomato Restaurant Recommendation  
- **URL:** https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation  
- **Provider:** ManikaSaini (Hugging Face)

## Key Technical Components

1. **Data pipeline** — Load, clean, and filter restaurant records from Hugging Face
2. **Preference matching** — Apply user filters (location, budget, cuisine, rating, extras)
3. **LLM integration** — Prompt engineering for ranking, reasoning, and explanations
4. **Presentation layer** — Format and display top recommendations to the user

## Success Criteria

- User can specify preferences and receive personalized restaurant suggestions
- Recommendations are grounded in real dataset entries
- LLM provides human-like explanations for each suggestion
- Output is clear, structured, and actionable
