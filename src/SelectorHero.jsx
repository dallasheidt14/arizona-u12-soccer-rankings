import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const STATES = [
  "AZ","CA","CO","FL","GA","ID","IL","MI","MN","MO",
  "NC","NJ","NV","NY","OH","OR","PA","TN","TX","UT","VA","WA","WI"
];

const AGE_YEARS = Array.from({ length: 10 }, (_, i) => 2018 - i); // 2018..2009

export default function SelectorHero({ onSelect }) {
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("");
  const [state, setState] = useState("");

  const canSubmit = gender && age && state;

  // Add "scrolled" class for sticky header shadow
  useEffect(() => {
    const onScroll = () => {
      if (window.scrollY > 8) document.body.classList.add("scrolled");
      else document.body.classList.remove("scrolled");
    };
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    
    // Convert to API format and call onSelect
    const apiGender = gender === "boys" ? "MALE" : "FEMALE";
    onSelect && onSelect({ 
      gender: apiGender, 
      age: age, 
      state: state 
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 text-white">
      {/* Sticky header */}
      <header
        className="sticky top-0 z-50 w-full bg-slate-900/80 backdrop-blur-md border-b border-white/10
                   transition-shadow duration-300 shadow-md"
      >
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight">Youth Soccer Rankings</h1>
          <p className="text-slate-300 text-sm md:text-base">
            Select your criteria to view team rankings & histories
          </p>
        </div>
      </header>

      {/* Hero section */}
      <main className="relative mx-auto max-w-6xl px-4 py-10 md:py-16">
        {/* Subtle soccer-pitch lines (decor only) */}
        <SoccerPitchBg />

        <AnimatePresence>
          <motion.section
            key="selector"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
            className="relative mx-auto w-full max-w-xl rounded-2xl bg-white/10 backdrop-blur-xl
                       border border-white/15 shadow-2xl p-6 md:p-8"
            aria-labelledby="selector-title"
          >
            <h2 id="selector-title" className="text-2xl font-semibold mb-1">Choose Division</h2>
            <p className="text-slate-300 mb-6">
              Gender, age group (BY year), and state. You'll see rankings with drill-downs.
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Gender */}
              <div>
                <label className="block text-sm font-semibold mb-2" htmlFor="gender">
                  Gender
                </label>
                <div id="gender" className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    aria-pressed={gender === "boys"}
                    onClick={() => setGender("boys")}
                    className={`rounded-lg py-3 font-semibold transition-all border
                      ${gender === "boys"
                        ? "bg-emerald-500 hover:bg-emerald-400 border-emerald-400 shadow-lg"
                        : "bg-white/10 hover:bg-white/20 border-white/20"
                      }`}
                  >
                    ⚽ Boys
                  </button>
                  <button
                    type="button"
                    aria-pressed={gender === "girls"}
                    onClick={() => setGender("girls")}
                    className={`rounded-lg py-3 font-semibold transition-all border
                      ${gender === "girls"
                        ? "bg-emerald-500 hover:bg-emerald-400 border-emerald-400 shadow-lg"
                        : "bg-white/10 hover:bg-white/20 border-white/20"
                      }`}
                  >
                    🏆 Girls
                  </button>
                </div>
              </div>

              {/* Age */}
              <div>
                <label htmlFor="age" className="block text-sm font-semibold mb-2">
                  Age Group (Birth Year)
                </label>
                <select
                  id="age"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className="w-full rounded-lg bg-white/10 border border-white/20 px-4 py-3
                             outline-none focus:ring-2 focus:ring-emerald-400 text-white"
                >
                  <option value="">Select Birth Year</option>
                  {AGE_YEARS.map((yr) => (
                    <option key={yr} value={yr} style={{ color: '#1e293b' }}>{yr}</option>
                  ))}
                </select>
              </div>

              {/* State */}
              <div>
                <label htmlFor="state" className="block text-sm font-semibold mb-2">State</label>
                <select
                  id="state"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full rounded-lg bg-white/10 border border-white/20 px-4 py-3
                             outline-none focus:ring-2 focus:ring-emerald-400 text-white"
                >
                  <option value="">Select State</option>
                  {STATES.map((s) => (
                    <option key={s} value={s} style={{ color: '#1e293b' }}>{s}</option>
                  ))}
                </select>
              </div>

              {/* CTA */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className={`w-full rounded-lg py-3 font-bold tracking-wide
                    transition-all shadow-md motion-safe:animate-pulse
                    ${canSubmit
                      ? "bg-emerald-500 hover:bg-emerald-400 hover:shadow-lg"
                      : "bg-emerald-500/40 cursor-not-allowed"
                    }`}
                >
                  Show Rankings →
                </button>
                <p className="mt-2 text-xs text-slate-300">
                  Data window: last 12 months, up to 30 most recent matches (reduced weight for 26–30).
                </p>
              </div>
            </form>
          </motion.section>
        </AnimatePresence>
      </main>
    </div>
  );
}

/** Decorative background: subtle soccer pitch lines */
function SoccerPitchBg() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10 opacity-20"
    >
      <svg
        className="w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M 80 0 L 0 0 0 80" fill="none" stroke="white" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <circle cx="50%" cy="45%" r="64" fill="none" stroke="white" strokeWidth="0.75" />
        <line x1="0" y1="45%" x2="100%" y2="45%" stroke="white" strokeWidth="0.75" />
      </svg>
    </div>
  );
}




