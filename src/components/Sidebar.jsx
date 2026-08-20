import { Link } from "react-router-dom";
import LastWinningBet from "./cards/LastWinningBet";
import SidebarMarketCards from "./SidebarMarketCards";

const categories = [
  { label: "Top Markets", icon: "🔥", count: 10 },
  { label: "High Probability", icon: "🎯", count: 8 },
  { label: "Trending", icon: "📈", count: 10 },
  { label: "New Markets", icon: "🆕", count: 6 },
  { label: "Crypto", icon: "₿", count: 10 },
  { label: "Politics", icon: "🏛️", count: 6 },
  { label: "Sports", icon: "🏆", count: 15 },
  { label: "Economy", icon: "🌍", count: 10 },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-premiumDark border-r border-white/5 p-4 space-y-4">

      {/* BRAND */}
      <div className="text-xl font-semibold">
        Polymarket <span className="opacity-60">Premium</span>
      </div>

      {/* 🔥 WINNING CLAIM — MOVED TO TOP */}
      <LastWinningBet />

      {/* LIVE | MOCK | RESOLVED ANALYTICS */}
      <nav className="space-y-1">
        <Link
          to="/analytics"
          className="flex items-center justify-between px-3 py-2 rounded-lg
                     text-sm cursor-pointer text-white hover:bg-white/10
                     border border-emerald-500/30 bg-emerald-500/10"
        >
          <span className="flex items-center gap-2">
            <span>📊</span>
            <span>Live · Mock · Resolved</span>
          </span>
          <span className="text-[11px] text-emerald-300/70">API</span>
        </Link>
      </nav>

      {/* CATEGORIES */}
      <nav className="space-y-1">
        {categories.map((c) => (
          <div
            key={c.label}
            className="flex items-center justify-between px-3 py-2
                       rounded-lg text-sm cursor-pointer
                       text-white/80 hover:bg-white/5"
          >
            <div className="flex items-center gap-2">
              <span>{c.icon}</span>
              <span>{c.label}</span>
            </div>
            <span className="text-[11px] text-white/40">
              {c.count} bets
            </span>
          </div>
        ))}
      </nav>

      {/* ONGOING + UPCOMING */}
      <SidebarMarketCards />

    </aside>
  );
}