// src/components/AnalyticsDashboard.jsx
// Real backend dashboard: Live | Mock | Resolved tabs, category filter,
// "Most Profitable Predictions" table, and CSV export.

import { useEffect, useMemo, useState } from "react";
import backendApi from "../services/backendApi";

const TABS = [
  { id: "live", label: "Live", desc: "Real-time markets (Gamma + CLOB)" },
  { id: "mock", label: "Mock", desc: "Simulated backtests" },
  { id: "resolved", label: "Resolved", desc: "Settled results / analytics" },
];

function fmtN(v) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function toCsv(rows) {
  if (!rows || rows.length === 0) return "";
  const cols = Object.keys(rows[0]);
  const esc = (v) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const head = cols.join(",");
  const body = rows.map((r) => cols.map((c) => esc(r[c])).join(",")).join("\n");
  return head + "\n" + body;
}

function downloadCsv(filename, rows) {
  const csv = toCsv(rows);
  if (!csv) return;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const CATEGORIES = ["", "politics", "sports", "crypto", "culture", "economy", "tech"];

export default function AnalyticsDashboard() {
  const [tab, setTab] = useState("live");
  const [category, setCategory] = useState("");
  const [health, setHealth] = useState(null);
  const [cats, setCats] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const h = await backendApi.health();
      setHealth(h);
      let prof = [];
      if (tab === "resolved") {
        prof = await backendApi.mostProfitable(category || "", 25);
      }
      setRows(prof);
      const c = await backendApi.categories();
      setCats(Array.isArray(c) ? c : []);
    } catch (e) {
      setError("Backend not reachable. Start it with: make api   (" + e.message + ")");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, category]);

  async function runIngest() {
    setLoading(true);
    setError("");
    try {
      let res;
      if (tab === "live") res = await backendApi.ingestLive(30);
      else if (tab === "mock") res = await backendApi.ingestMock(80);
      else res = await backendApi.ingestResolved(100);
      setLastRun(res);
      await refresh();
    } catch (e) {
      setError("Ingest failed: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  const exportRows = useMemo(() => {
    if (tab === "live" && health) {
      return [
        { schema: "live", table: "markets", rows: health.live_markets ?? 0 },
        { schema: "live", table: "prices", rows: health.live_prices ?? 0 },
        { schema: "mock", table: "trades", rows: health.mock_trades ?? 0 },
        { schema: "mock", table: "runs", rows: health.mock_runs ?? 0 },
        { schema: "resolved", table: "markets", rows: health.resolved_markets ?? 0 },
        { schema: "resolved", table: "predictions", rows: health.resolved_predictions ?? 0 },
      ];
    }
    if (tab === "resolved") return rows;
    if (tab === "mock") return cats;
    return rows;
  }, [tab, health, rows, cats]);

  return (
    <div className="text-white">
      {/* Header */}
      <header className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            📊 PolyMarket Analytics
          </h1>
          <p className="text-xs text-white/40 mt-1">
            Most Profitable Predictions by category · Live | Mock | Resolved
          </p>
        </div>
        <div className="flex gap-2 items-center">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="bg-black/50 border border-white/10 rounded px-3 py-2 text-sm text-white/80"
        >
          <option value="">All categories</option>
          {CATEGORIES.filter(Boolean).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={refresh}
          disabled={loading}
          className="px-3 py-2 text-sm rounded bg-white/10 hover:bg-white/20 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
        </div>
      </header>

      {error && (
        <div className="mt-4 p-3 rounded bg-red-500/15 border border-red-500/40 text-sm text-red-200">
          ⚠️ {error}
        </div>
      )}

      {/* Health strip */}
      {health && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          {Object.entries(health).filter(([k]) => k !== "service" && k !== "database" && k !== "status").map(([k, v]) => (
            <div key={k} className="bg-white/5 rounded p-3">
              <div className="text-white/40 uppercase tracking-wide">{k.replace(/_/g, " ")}</div>
              <div className="text-lg font-semibold">{fmtN(v)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="mt-6 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={
              "px-4 py-2 rounded text-sm font-medium transition " +
              (tab === t.id
                ? "bg-white text-black"
                : "bg-white/5 text-white/70 hover:bg-white/10")
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab body */}
      <div className="mt-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <p className="text-xs text-white/50">
            {TABS.find((t) => t.id === tab)?.desc}
          </p>
          <div className="flex gap-2">
            <button
              onClick={runIngest}
              disabled={loading}
              className="px-3 py-1.5 text-xs rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50"
            >
              ▲ Run {tab} ingest
            </button>
            <button
              onClick={() =>
                downloadCsv(
                  "polymarket_" + tab + ".csv",
                  exportRows
                )
              }
              className="px-3 py-1.5 text-xs rounded bg-white/10 hover:bg-white/20"
            >
              ⬇ Export CSV
            </button>
          </div>
        </div>

        {lastRun && (
          <p className="mt-3 text-xs text-emerald-300/80">
            Last ingest: {JSON.stringify(lastRun)}
          </p>
        )}

        {/* Lazy note for mock tab */}
        {tab === "mock" && (
          <div className="mt-4 bg-white/5 rounded p-4 text-sm text-white/60">
            <strong>Mock backtests:</strong> run simulated strategies on the mock schema.
            Category performance is shown in the Resolved tab.
          </div>
        )}

        {/* Category performance table (all tabs show store counts/categories) */}
        {(tab === "live" || tab === "mock" || tab === "resolved") && (
          <div className="mt-4">
            <h2 className="text-sm font-semibold text-white/70 mb-2">
              {tab === "resolved" ? "Most Profitable Predictions" : "Category Performance"}
            </h2>
            <div className="overflow-x-auto border border-white/10 rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-white/40 bg-white/5">
                    {tab === "resolved" && rows.length > 0 &&
                      Object.keys(rows[0]).map((k) => (
                        <th key={k} className="px-3 py-2 font-medium">{k.replace(/_/g, " ")}</th>
                      ))}
                    {tab !== "resolved" && (
                      <>
                        <th className="px-3 py-2 font-medium">Category</th>
                        <th className="px-3 py-2 font-medium">Total</th>
                        <th className="px-3 py-2 font-medium">Win rate %</th>
                        <th className="px-3 py-2 font-medium">ROI %</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {tab === "resolved" && rows.length > 0 ? (
                    rows.map((r, i) => (
                      <tr key={i} className="border-t border-white/5">
                        {Object.entries(r).map(([k, v], j) => (
                          <td key={j} className="px-3 py-2 text-white/80">
                            {k.includes("prob") && typeof v === "number" && v > 1
                              ? fmtN(v)
                              : typeof v === "number"
                              ? fmtN(Number(v.toFixed ? v.toFixed(3) : v))
                              : String(v)}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : tab !== "resolved" ? (
                    cats.map((c) => (
                      <tr key={c.category} className="border-t border-white/5">
                        <td className="px-3 py-2 capitalize text-white/80">{c.category}</td>
                        <td className="px-3 py-2 text-white/80">{fmtN(c.total_markets)}</td>
                        <td className="px-3 py-2 text-white/80">{fmtN(c.win_rate_pct)}</td>
                        <td className={"px-3 py-2 " + (c.roi_pct < 0 ? "text-red-300" : "text-emerald-300")}>
                          {fmtN(c.roi_pct)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr><td className="px-3 py-4 text-white/40">No resolved data yet — click “Run resolved ingest”.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
