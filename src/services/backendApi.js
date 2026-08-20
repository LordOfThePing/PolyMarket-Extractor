// src/services/backendApi.js
// Thin client for the FastAPI backend (routed through the Vite dev proxy).
// In production, set VITE_API_BASE to the deployed API URL.

const API_BASE = import.meta.env.VITE_API_BASE || "/api";
// Health lives at /health (not /api/*); proxy forwards both.
const HEALTH_BASE = import.meta.env.VITE_HEALTH_BASE || "/health";

async function request(base, path, options = {}) {
  const res = await fetch(base + path, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || path}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export const backendApi = {
  // Health / counts
  health: () => request(HEALTH_BASE, ""),

  // Ingestion
  ingestLive: (limit = 30) =>
    request(API_BASE, "/ingest/live?limit=" + limit, { method: "POST" }),
  ingestMock: (nTrades = 60, strategy = "confidence_threshold") =>
    request(
      API_BASE,
      "/ingest/mock?n_trades=" + nTrades + "&strategy=" + encodeURIComponent(strategy),
      { method: "POST" }
    ),
  ingestResolved: (limit = 100) =>
    request(API_BASE, "/ingest/resolved?limit=" + limit, { method: "POST" }),

  // Analytics
  categories: () => request(API_BASE, "/analytics/categories"),
  mostProfitable: (category, limit = 20) => {
    const q =
      "?limit=" + limit + (category ? "&category=" + encodeURIComponent(category) : "");
    return request(API_BASE, "/analytics/most-profitable" + q);
  },
  mockRuns: () => request(API_BASE, "/analytics/mock-runs"),
};

export default backendApi;
