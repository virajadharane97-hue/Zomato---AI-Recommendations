import { useState, useEffect } from 'react';
import { UtensilsCrossed, Star, Moon, Sun, Menu, X } from 'lucide-react';
import { HomePage } from '@/pages/HomePage';

function App() {
  const [dark, setDark] = useState<boolean>(() => {
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  return (
    <div className="min-h-screen bg-[#f9f9f9] dark:bg-[#111111] text-[#1a1c1c] dark:text-[#f0f0f0] font-sans">
      {/* Top Navigation Bar */}
      <header className="fixed top-0 w-full h-16 z-50 bg-[#f9f9f9] dark:bg-[#1e1e1e] shadow-sm flex items-center">
        <div className="flex justify-between items-center px-12 w-full max-w-[1280px] mx-auto">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <UtensilsCrossed className="text-[#b7122a]" size={24} />
            <Star className="text-[#feae2c]" size={20} fill="#feae2c" />
            <div className="flex flex-col">
              <span className="text-xl font-bold text-[#b7122a] leading-tight">ZomatoAI</span>
              <span className="text-[11px] text-[#5b403f] dark:text-[#9a9a9a] leading-tight hidden sm:block">
                AI-Powered Restaurant Recommendations
              </span>
            </div>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex gap-6 h-full items-center">
            <a
              href="#"
              className="text-[#b7122a] border-b-2 border-[#b7122a] pb-0.5 font-semibold text-sm transition-colors"
            >
              Explore
            </a>
            <a
              href="#"
              className="text-[#5b403f] dark:text-[#9a9a9a] hover:text-[#b7122a] font-semibold text-sm transition-colors"
            >
              History
            </a>
            <a
              href="#"
              className="text-[#5b403f] dark:text-[#9a9a9a] hover:text-[#b7122a] font-semibold text-sm transition-colors"
            >
              Saved
            </a>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDark((d) => !d)}
              className="p-2 rounded-full text-[#5b403f] dark:text-[#9a9a9a] hover:text-[#b7122a] hover:bg-[#eeeeee] dark:hover:bg-[#2e2e2e] transition-colors"
              aria-label="Toggle dark mode"
            >
              {dark ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-2 rounded-full text-[#5b403f] dark:text-[#9a9a9a] hover:bg-[#eeeeee] dark:hover:bg-[#2e2e2e] transition-colors"
              onClick={() => setMobileMenuOpen((o) => !o)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div className="absolute top-16 left-0 w-full bg-[#f9f9f9] dark:bg-[#1e1e1e] border-t border-[#e4bebc] dark:border-[#2e2e2e] flex flex-col px-4 py-3 gap-3 md:hidden shadow-md">
            <a href="#" className="text-[#b7122a] font-semibold text-sm py-1">Explore</a>
            <a href="#" className="text-[#5b403f] dark:text-[#9a9a9a] text-sm py-1">History</a>
            <a href="#" className="text-[#5b403f] dark:text-[#9a9a9a] text-sm py-1">Saved</a>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="pt-16">
        <HomePage />
      </main>
    </div>
  );
}

export default App;
