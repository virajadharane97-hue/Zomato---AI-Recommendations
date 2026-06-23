import { X, AlertTriangle } from 'lucide-react';
import type { RecommendRequest } from '@/types/api';

interface FilterBadgesProps {
  filters: RecommendRequest;
  relaxedFilters?: string[];
}

export function FilterBadges({ filters, relaxedFilters }: FilterBadgesProps) {
  const badges = [
    { key: 'location', label: filters.location },
    { key: 'budget', label: `${filters.budget.charAt(0).toUpperCase() + filters.budget.slice(1)} Budget` },
    filters.cuisine ? { key: 'cuisine', label: filters.cuisine } : null,
    { key: 'rating', label: `${filters.min_rating?.toFixed(1) ?? '0.0'}+ Rating` },
  ].filter(Boolean) as { key: string; label: string }[];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2 flex-wrap">
        {badges.map(({ key, label }) => (
          <div
            key={key}
            className="bg-[#f3f3f3] dark:bg-[#2a2a2a] border border-[#e4bebc] dark:border-[#3a3a3a] rounded-full px-3 py-1 flex items-center gap-1"
          >
            <span className="text-sm text-[#5b403f] dark:text-[#9a9a9a]">{label}</span>
            <X size={14} className="text-[#5b403f] dark:text-[#9a9a9a] cursor-pointer hover:text-[#ba1a1a]" />
          </div>
        ))}
      </div>
      {relaxedFilters && relaxedFilters.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-[#835500] dark:text-[#feae2c] bg-[#ffddb4]/30 dark:bg-[#2a2010] border border-[#feae2c]/40 rounded-lg px-3 py-1.5">
          <AlertTriangle size={13} />
          <span>
            Some filters were relaxed to find results: {relaxedFilters.join(', ')}
          </span>
        </div>
      )}
    </div>
  );
}
