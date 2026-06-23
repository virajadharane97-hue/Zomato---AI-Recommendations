import { Sparkles } from 'lucide-react';

interface SummaryBannerProps {
  summary: string;
}

export function SummaryBanner({ summary }: SummaryBannerProps) {
  return (
    <div className="w-full bg-gradient-to-r from-[#f3e0c6] to-[#ffffff] dark:from-[#2a2010] dark:to-[#1e1e1e] border border-[#d6c4ab] dark:border-[#3a2e1a] rounded-xl p-4 flex items-start gap-4 shadow-sm fade-in-up">
      <div className="bg-white dark:bg-[#2a2010] p-2 rounded-full shadow-sm shrink-0">
        <Sparkles size={20} className="text-[#feae2c]" />
      </div>
      <div>
        <p className="text-sm font-semibold text-[#5b403f] dark:text-[#feae2c] uppercase tracking-wider mb-1">
          AI Summary
        </p>
        <p className="text-[15px] text-[#1a1c1c] dark:text-[#f0f0f0] italic leading-relaxed">
          "{summary}"
        </p>
      </div>
    </div>
  );
}
