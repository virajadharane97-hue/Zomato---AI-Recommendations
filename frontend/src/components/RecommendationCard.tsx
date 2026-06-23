import { Star, Brain, IndianRupee } from 'lucide-react';
import type { RecommendationItem } from '@/types/api';

interface RecommendationCardProps {
  item: RecommendationItem;
  delay?: number;
}

const RANK_STYLES: Record<number, { bg: string; ring: string; text: string }> = {
  1: { bg: '#FFD700', ring: 'ring-2 ring-[#FFD700]/30', text: 'text-[#1a1c1c]' },
  2: { bg: '#C0C0C0', ring: 'ring-1 ring-[#C0C0C0]/50', text: 'text-[#1a1c1c]' },
  3: { bg: '#CD7F32', ring: 'ring-1 ring-[#CD7F32]/50', text: 'text-white' },
};

function getRatingColor(rating: number): string {
  if (rating >= 4.5) return 'bg-green-700';
  if (rating >= 4.0) return 'bg-green-600';
  if (rating >= 3.5) return 'bg-yellow-500';
  return 'bg-orange-500';
}

// Extract cuisine tags from comma-separated string
function parseCuisines(cuisine: string): string[] {
  return cuisine
    .split(',')
    .map((c) => c.trim())
    .filter(Boolean)
    .slice(0, 4);
}

const TAG_COLORS = [
  'bg-[#b7122a]/10 text-[#b7122a]',
  'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  'bg-[#e8e8e8] text-[#5b403f] dark:bg-[#2a2a2a] dark:text-[#9a9a9a]',
  'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
];

export function RecommendationCard({ item, delay = 0 }: RecommendationCardProps) {
  const rankStyle = RANK_STYLES[item.rank] ?? { bg: '#888888', ring: '', text: 'text-white' };
  const tags = parseCuisines(item.cuisine);

  return (
    <article
      className={`bg-[#f9f9f9] dark:bg-[#1e1e1e] rounded-xl border border-[#e4bebc] dark:border-[#2e2e2e] overflow-hidden card-shadow transition-all relative fade-in-up flex flex-col h-full ${rankStyle.ring}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Rank Badge */}
      <div
        className="absolute top-2 left-2 z-10 px-2 py-1 rounded-full flex items-center gap-1 shadow-md"
        style={{ backgroundColor: rankStyle.bg }}
      >
        <Star size={12} className={rankStyle.text} fill="currentColor" />
        <span className={`text-[11px] font-bold tracking-wider ${rankStyle.text}`}>
          RANK {item.rank}
        </span>
      </div>

      {/* Placeholder image area — skipped per user request */}
      <div className="h-10" />

      {/* Card Body */}
      <div className="p-4 flex flex-col flex-1 gap-2">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold text-[#1a1c1c] dark:text-[#f0f0f0] leading-tight">
            {item.name}
          </h3>
          <div className={`${getRatingColor(item.rating)} text-white px-1.5 py-0.5 rounded flex items-center gap-1 shrink-0 ml-2`}>
            <span className="text-xs font-semibold">{item.rating.toFixed(1)}</span>
            <Star size={10} fill="white" />
          </div>
        </div>

        {/* Cost */}
        <div className="flex items-center gap-1 text-xs text-[#5b403f] dark:text-[#9a9a9a]">
          <IndianRupee size={12} />
          <span>{item.estimated_cost.toLocaleString('en-IN')} for two</span>
        </div>

        {/* Cuisine tags */}
        <div className="flex gap-1.5 flex-wrap mt-1">
          {tags.map((tag, i) => (
            <span
              key={tag}
              className={`${TAG_COLORS[i % TAG_COLORS.length]} px-2 py-0.5 rounded-full text-[11px] font-semibold`}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* AI Insight Block */}
      <div className="border-l-4 border-[#feae2c] ai-tint dark:bg-[#2a2010] p-3 mx-4 mb-4 rounded-r-lg">
        <div className="flex items-center gap-1 mb-1">
          <Brain size={13} className="text-[#835500] dark:text-[#feae2c]" />
          <span className="text-[11px] font-bold tracking-wider text-[#835500] dark:text-[#feae2c] uppercase">
            AI Insight
          </span>
        </div>
        <p className="text-xs text-[#5b403f] dark:text-[#c0a080] leading-relaxed">
          {item.explanation}
        </p>
      </div>
    </article>
  );
}
