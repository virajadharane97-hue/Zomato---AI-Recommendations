import { RecommendationCard } from './RecommendationCard';
import type { RecommendationItem } from '@/types/api';

interface ResultsGridProps {
  items: RecommendationItem[];
}

export function ResultsGrid({ items }: ResultsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {items.map((item, idx) => (
        <RecommendationCard
          key={`${item.rank}-${item.name}`}
          item={item}
          delay={idx * 100}
        />
      ))}
    </div>
  );
}
