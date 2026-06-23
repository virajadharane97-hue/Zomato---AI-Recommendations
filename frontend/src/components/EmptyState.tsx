import { SearchX, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  onRetry?: () => void;
}

export function EmptyState({ onRetry }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center fade-in-up">
      <div className="w-20 h-20 bg-[#eeeeee] dark:bg-[#2a2a2a] rounded-full flex items-center justify-center mb-4">
        <SearchX size={36} className="text-[#5b403f] dark:text-[#9a9a9a]" />
      </div>
      <h3 className="text-lg font-semibold text-[#1a1c1c] dark:text-[#f0f0f0] mb-2">
        No restaurants found
      </h3>
      <p className="text-sm text-[#5b403f] dark:text-[#9a9a9a] max-w-xs mb-2">
        We couldn't find any restaurants matching your preferences.
      </p>
      <ul className="text-sm text-[#5b403f] dark:text-[#9a9a9a] mb-6 text-left list-disc list-inside space-y-1">
        <li>Try a different location</li>
        <li>Broaden your budget range</li>
        <li>Lower the minimum rating</li>
        <li>Remove the cuisine filter</li>
      </ul>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 bg-[#b7122a] hover:bg-[#bb162c] text-white font-semibold text-sm py-2.5 px-5 rounded-lg transition-colors active:scale-95"
        >
          <RefreshCw size={16} />
          Adjust Filters
        </button>
      )}
    </div>
  );
}
