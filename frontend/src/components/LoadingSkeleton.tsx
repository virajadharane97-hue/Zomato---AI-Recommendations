function SkeletonCard({ delay = 0 }: { delay?: number }) {
  return (
    <div
      className="bg-[#f9f9f9] dark:bg-[#1e1e1e] rounded-xl border border-[#e4bebc] dark:border-[#2e2e2e] overflow-hidden flex flex-col h-full relative"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Rank badge skeleton */}
      <div className="absolute top-2 left-2 w-16 h-6 rounded-full ai-shimmer z-10" />
      {/* Image area skeleton */}
      <div className="w-full h-10 ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
      <div className="p-4 flex-grow flex flex-col gap-3">
        <div className="flex justify-between items-start">
          <div className="h-5 w-3/4 rounded ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
          <div className="h-5 w-10 rounded ai-shimmer ml-2" style={{ animationDelay: `${delay}ms` }} />
        </div>
        <div className="h-4 w-1/3 rounded ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
        <div className="flex gap-1.5 mt-1">
          <div className="h-5 w-14 rounded-full ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
          <div className="h-5 w-20 rounded-full ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
          <div className="h-5 w-16 rounded-full ai-shimmer" style={{ animationDelay: `${delay}ms` }} />
        </div>
      </div>
      {/* AI Insight skeleton */}
      <div className="p-3 mx-4 mb-4 rounded-r-lg border-l-4 border-[#feae2c] ai-shimmer">
        <div className="h-3 w-full rounded bg-[#e8e8e8] dark:bg-[#333] opacity-50 mb-1.5" />
        <div className="h-3 w-4/5 rounded bg-[#e8e8e8] dark:bg-[#333] opacity-50" />
      </div>
    </div>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {/* Summary banner skeleton */}
      <div className="w-full bg-[#f3f3f3] dark:bg-[#1e1e1e] rounded-xl p-4 border border-[#e4bebc] dark:border-[#2e2e2e] flex items-start gap-4">
        <div className="w-10 h-10 rounded-full ai-shimmer shrink-0" />
        <div className="flex-grow space-y-2 pt-1">
          <div className="h-5 w-1/3 rounded ai-shimmer" />
          <div className="h-4 w-full rounded ai-shimmer" />
          <div className="h-4 w-5/6 rounded ai-shimmer" />
          <div className="h-4 w-2/3 rounded ai-shimmer" />
        </div>
      </div>

      {/* Cards grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} delay={i * 80} />
        ))}
      </div>
    </div>
  );
}
