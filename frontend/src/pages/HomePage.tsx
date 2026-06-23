import { useState, useRef } from 'react';
import { UtensilsCrossed, AlertCircle, RefreshCw } from 'lucide-react';
import { PreferenceForm } from '@/components/PreferenceForm';
import { SummaryBanner } from '@/components/SummaryBanner';
import { FilterBadges } from '@/components/FilterBadges';
import { ResultsGrid } from '@/components/ResultsGrid';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { EmptyState } from '@/components/EmptyState';
import { postRecommend } from '@/lib/api';
import type { RecommendRequest, RecommendResponse } from '@/types/api';

type PageState = 'idle' | 'loading' | 'success' | 'empty' | 'error';

export function HomePage() {
  const [state, setState] = useState<PageState>('idle');
  const [response, setResponse] = useState<RecommendResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<RecommendRequest | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async (req: RecommendRequest) => {
    setState('loading');
    setLastRequest(req);
    setErrorMsg('');

    try {
      const res = await postRecommend(req);
      setResponse(res);
      if (res.recommendations.length === 0) {
        setState('empty');
      } else {
        setState('success');
        // Scroll to results
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    } catch (err: unknown) {
      const msg =
        typeof err === 'object' && err !== null && 'detail' in err
          ? String((err as { detail: unknown }).detail)
          : 'Something went wrong. Please try again.';
      setErrorMsg(msg);
      setState('error');
    }
  };

  const handleRetry = () => {
    if (lastRequest) void handleSubmit(lastRequest);
  };

  // Extract relaxed filters from metadata if present
  const relaxedFilters = (() => {
    if (!response?.metadata?.filters_applied) return [];
    const fa = response.metadata.filters_applied as Record<string, unknown>;
    if (Array.isArray(fa.relaxed)) return fa.relaxed as string[];
    return [];
  })();

  return (
    <>
      {/* Hero Section */}
      <section className="h-[180px] bg-gradient-to-r from-[#b7122a] to-[#feae2c] text-white flex items-center justify-center relative overflow-hidden">
        {/* Dot pattern overlay */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='2' fill='rgba(255,255,255,0.5)'/%3E%3C/svg%3E\")",
          }}
        />
        <div className="relative z-10 text-center flex flex-col items-center gap-2">
          <div className="flex gap-2 items-center justify-center">
            <UtensilsCrossed size={32} className="text-white" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold drop-shadow-md">
            Find Your Perfect Restaurant
          </h1>
          <p className="text-sm text-white/80">
            AI-curated recommendations tailored to your taste
          </p>
        </div>
      </section>

      {/* Main Content */}
      <div className="max-w-[1280px] mx-auto px-4 md:px-12 mt-6 pb-12">
        <div className="flex gap-6 items-start">
          {/* Left Sidebar — Preferences Form */}
          <div className="hidden md:block">
            <PreferenceForm onSubmit={handleSubmit} loading={state === 'loading'} />
          </div>

          {/* Right Panel — Results */}
          <div className="flex-1 flex flex-col gap-5 min-w-0">
            {/* Mobile form */}
            <div className="md:hidden">
              <PreferenceForm onSubmit={handleSubmit} loading={state === 'loading'} />
            </div>

            {/* Idle state — prompt */}
            {state === 'idle' && (
              <div className="flex flex-col items-center justify-center py-20 text-center fade-in-up">
                <div className="w-20 h-20 bg-[#eeeeee] dark:bg-[#2a2a2a] rounded-full flex items-center justify-center mb-4">
                  <UtensilsCrossed size={36} className="text-[#b7122a]" />
                </div>
                <h2 className="text-xl font-semibold text-[#1a1c1c] dark:text-[#f0f0f0] mb-2">
                  Ready to discover great food?
                </h2>
                <p className="text-sm text-[#5b403f] dark:text-[#9a9a9a] max-w-xs">
                  Set your preferences on the left and click "Find Restaurants" to get AI-powered recommendations.
                </p>
              </div>
            )}

            {/* Loading state */}
            {state === 'loading' && <LoadingSkeleton />}

            {/* Error state */}
            {state === 'error' && (
              <div className="flex flex-col items-center gap-4 py-12 fade-in-up">
                <div className="flex items-center gap-2 text-[#ba1a1a] bg-[#ffdad6] dark:bg-[#3a1010] border border-[#ba1a1a]/30 rounded-xl px-4 py-3 max-w-md w-full">
                  <AlertCircle size={18} />
                  <p className="text-sm font-medium">{errorMsg}</p>
                </div>
                <button
                  onClick={handleRetry}
                  className="flex items-center gap-2 text-sm text-[#b7122a] hover:underline"
                >
                  <RefreshCw size={14} />
                  Try again
                </button>
              </div>
            )}

            {/* Success state */}
            {state === 'success' && response && (
              <div ref={resultsRef} className="flex flex-col gap-5">
                {/* Filter badges */}
                {lastRequest && (
                  <FilterBadges filters={lastRequest} relaxedFilters={relaxedFilters} />
                )}
                {/* Summary banner */}
                {response.summary && <SummaryBanner summary={response.summary} />}
                {/* Results grid */}
                <ResultsGrid items={response.recommendations} />
                {/* Metadata */}
                {response.metadata.candidates_considered > 0 && (
                  <p className="text-xs text-[#5b403f] dark:text-[#666] text-center">
                    {response.metadata.candidates_considered} restaurants evaluated ·{' '}
                    {response.metadata.model
                      ? `Model: ${response.metadata.model}`
                      : 'Heuristic ranking'}
                  </p>
                )}
              </div>
            )}

            {/* Empty state */}
            {state === 'empty' && (
              <div ref={resultsRef}>
                {lastRequest && <FilterBadges filters={lastRequest} />}
                <EmptyState onRetry={() => setState('idle')} />
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
