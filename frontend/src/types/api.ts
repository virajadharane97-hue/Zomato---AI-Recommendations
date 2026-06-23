// TypeScript types mirroring the FastAPI Pydantic schemas

export interface RecommendRequest {
  location: string;
  budget: 'low' | 'medium' | 'high';
  cuisine?: string | null;
  min_rating?: number;
  additional?: string | null;
}

export interface RecommendationItem {
  rank: number;
  name: string;
  cuisine: string;
  rating: number;
  estimated_cost: number;
  explanation: string;
}

export interface RecommendationMetadata {
  candidates_considered: number;
  filters_applied: Record<string, unknown>;
  model: string;
}

export interface RecommendResponse {
  summary: string | null;
  recommendations: RecommendationItem[];
  metadata: RecommendationMetadata;
}

export interface HealthResponse {
  status: string;
  dataset_loaded: boolean;
}

export interface LocationsResponse {
  locations: string[];
  count: number;
}

export interface CuisinesResponse {
  cuisines: string[];
  count: number;
}

export interface ApiError {
  detail: string;
  suggestions?: Record<string, string[]>;
}
