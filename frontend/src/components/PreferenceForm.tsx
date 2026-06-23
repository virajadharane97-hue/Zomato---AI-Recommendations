import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { MapPin, ChevronDown, UtensilsCrossed, Star, Search, Loader2 } from 'lucide-react';
import { getLocations, getCuisines } from '@/lib/api';
import type { RecommendRequest } from '@/types/api';

const schema = z.object({
  location: z.string().min(1, 'Location is required'),
  budget: z.enum(['low', 'medium', 'high'] as const, { error: 'Budget is required' }),
  cuisine: z.string().optional(),
  min_rating: z.number().min(0).max(5),
  additional: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface PreferenceFormProps {
  onSubmit: (data: RecommendRequest) => void;
  loading: boolean;
}

const BUDGET_OPTIONS = [
  { value: 'low' as const, emoji: '🥗', label: 'Low', hint: '≤ ₹500' },
  { value: 'medium' as const, emoji: '🍱', label: 'Medium', hint: '₹501–1,500' },
  { value: 'high' as const, emoji: '🥩', label: 'High', hint: '₹1,500+' },
];

export function PreferenceForm({ onSubmit, loading }: PreferenceFormProps) {
  const [locations, setLocations] = useState<string[]>([]);
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [locLoading, setLocLoading] = useState(true);

  const {
    register,
    handleSubmit: rhfSubmitHandler,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      budget: 'medium',
      min_rating: 3.5,
      additional: '',
    },
  });

  const selectedBudget = watch('budget');
  const minRating = watch('min_rating');

  useEffect(() => {
    async function load() {
      try {
        console.log('Fetching locations and cuisines...');
        const [locRes, cuiRes] = await Promise.all([getLocations(), getCuisines()]);
        console.log('Locations received:', locRes.locations.length);
        console.log('Cuisines received:', cuiRes.cuisines.length);
        setLocations(locRes.locations);
        setCuisines(cuiRes.cuisines);
      } catch (err) {
        console.error('Failed to load locations/cuisines:', err);
      } finally {
        setLocLoading(false);
      }
    }
    void load();
  }, []);

  const handleFormSubmit = (values: FormValues) => {
    console.log('Form submitted:', values);
    onSubmit({
      location: values.location,
      budget: values.budget,
      cuisine: values.cuisine || null,
      min_rating: values.min_rating,
      additional: values.additional || null,
    });
  };

  return (
    <aside className="w-[320px] shrink-0 bg-[#f9f9f9] dark:bg-[#1e1e1e] rounded-xl border border-[#e4bebc] dark:border-[#2e2e2e] p-4 flex flex-col gap-5 h-fit sticky top-24 card-shadow">
      <div>
        <h2 className="text-lg font-semibold text-[#1a1c1c] dark:text-[#f0f0f0]">Your Preferences</h2>
        <p className="text-xs text-[#5b403f] dark:text-[#9a9a9a] mt-0.5">Powered by ZomatoAI</p>
      </div>

      <form onSubmit={rhfSubmitHandler(handleFormSubmit)} className="flex flex-col gap-4">
        {/* Location */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold tracking-widest text-[#1a1c1c] dark:text-[#f0f0f0] uppercase">
            Location
          </label>
          <div className="relative">
            <MapPin
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5b403f] dark:text-[#9a9a9a]"
              size={16}
            />
            {locLoading ? (
              <div className="w-full bg-[#f3f3f3] dark:bg-[#2a2a2a] border border-[#e4bebc] dark:border-[#3a3a3a] rounded-lg py-2 pl-9 pr-4 text-sm text-[#5b403f] dark:text-[#9a9a9a] flex items-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Loading locations…
              </div>
            ) : (
              <select
                {...register('location')}
                onChange={(e) => {
                  setValue('location', e.target.value, { shouldValidate: true });
                }}
                className="w-full bg-[#f3f3f3] dark:bg-[#2a2a2a] border border-[#e4bebc] dark:border-[#3a3a3a] rounded-lg py-2 pl-9 pr-8 text-sm text-[#1a1c1c] dark:text-[#f0f0f0] focus:outline-none focus:ring-2 focus:ring-[#b7122a]"
              >
                <option value="">Select a location…</option>
                {locations.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
            )}
            <ChevronDown
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5b403f] dark:text-[#9a9a9a] pointer-events-none"
              size={16}
            />
          </div>
          {errors.location && (
            <p className="text-xs text-[#ba1a1a]">{errors.location.message}</p>
          )}
        </div>

        {/* Budget */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold tracking-widest text-[#1a1c1c] dark:text-[#f0f0f0] uppercase">
            Budget
          </label>
          <div className="flex flex-col gap-2">
            {BUDGET_OPTIONS.map(({ value, emoji, label, hint }) => {
              const active = selectedBudget === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setValue('budget', value)}
                  className={`w-full py-2 px-4 rounded-lg text-left flex items-center justify-between transition-colors ${
                    active
                      ? 'border-2 border-[#b7122a] bg-[#b7122a]/5 dark:bg-[#b7122a]/10'
                      : 'border border-[#e4bebc] dark:border-[#3a3a3a] hover:bg-[#f3f3f3] dark:hover:bg-[#2a2a2a]'
                  }`}
                >
                  <span
                    className={`text-sm font-${active ? 'semibold' : 'normal'} ${
                      active ? 'text-[#b7122a]' : 'text-[#1a1c1c] dark:text-[#f0f0f0]'
                    }`}
                  >
                    {emoji} {label}
                    <span className="ml-1 text-xs text-[#5b403f] dark:text-[#9a9a9a] font-normal">
                      {hint}
                    </span>
                  </span>
                  {active && (
                    <Search size={16} className="text-[#b7122a]" />
                  )}
                </button>
              );
            })}
          </div>
          {errors.budget && (
            <p className="text-xs text-[#ba1a1a]">{errors.budget.message}</p>
          )}
        </div>

        {/* Cuisine */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold tracking-widest text-[#1a1c1c] dark:text-[#f0f0f0] uppercase">
            Cuisine
          </label>
          <div className="relative">
            <UtensilsCrossed
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5b403f] dark:text-[#9a9a9a]"
              size={16}
            />
            <select
              {...register('cuisine')}
              className="w-full bg-[#f3f3f3] dark:bg-[#2a2a2a] border border-[#e4bebc] dark:border-[#3a3a3a] rounded-lg py-2 pl-9 pr-8 text-sm text-[#1a1c1c] dark:text-[#f0f0f0] focus:outline-none focus:ring-2 focus:ring-[#b7122a]"
            >
              <option value="">Any cuisine</option>
              {cuisines.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <ChevronDown
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5b403f] dark:text-[#9a9a9a] pointer-events-none"
              size={16}
            />
          </div>
        </div>

        {/* Min Rating */}
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold tracking-widest text-[#1a1c1c] dark:text-[#f0f0f0] uppercase">
              Min Rating
            </label>
            <div className="bg-[#e8e8e8] dark:bg-[#2a2a2a] px-2 py-0.5 rounded flex items-center gap-1">
              <span className="text-xs font-semibold text-[#1a1c1c] dark:text-[#f0f0f0]">
                {Number(minRating).toFixed(1)}
              </span>
              <Star size={12} className="text-[#feae2c]" fill="#feae2c" />
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={5}
            step={0.5}
            {...register('min_rating', { valueAsNumber: true })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-[#5b403f] dark:text-[#9a9a9a]">
            <span>0.0</span>
            <span>5.0</span>
          </div>
        </div>

        {/* Additional Preferences */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold tracking-widest text-[#1a1c1c] dark:text-[#f0f0f0] uppercase">
            Additional (optional)
          </label>
          <textarea
            {...register('additional')}
            rows={2}
            placeholder="e.g. family-friendly, outdoor seating, quiet atmosphere"
            className="w-full bg-[#f3f3f3] dark:bg-[#2a2a2a] border border-[#e4bebc] dark:border-[#3a3a3a] rounded-lg p-3 text-sm text-[#1a1c1c] dark:text-[#f0f0f0] placeholder:text-[#5b403f] dark:placeholder:text-[#666] focus:outline-none focus:ring-2 focus:ring-[#b7122a] resize-none"
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="mt-1 w-full bg-[#b7122a] hover:bg-[#bb162c] disabled:bg-[#e8e8e8] dark:disabled:bg-[#2a2a2a] text-white disabled:text-[#5b403f] dark:disabled:text-[#666] font-semibold text-base py-3 rounded-lg flex items-center justify-center gap-2 transition-colors active:scale-95 shadow-md"
        >
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Finding restaurants…
            </>
          ) : (
            <>
              Find Restaurants 🍽️
            </>
          )}
        </button>
      </form>
    </aside>
  );
}
