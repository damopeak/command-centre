// DEMO DATA - fake placeholder figures so the dashboard renders before the live /api/ endpoints answer.
// Nothing here is real: names, products, companies and amounts are invented for the design preview.
window.DATA = (() => {
  // Deterministic pseudo-random so the charts look the same on every reload
  let seed = 7;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  const series = (n, base, spread, trend = 0) =>
    Array.from({ length: n }, (_, i) => Math.max(0, Math.round(base + trend * i + (rnd() - 0.45) * spread)));

  return {
    user: { name: "" },

    // No demo figures: blanks until real Invenno data arrives
    fba: {
      today: { sales: null, profit: null, units: null, margin: null },
      month: { sales: null, profit: null, units: null, target: null },
      deltas: { profit: 0, sales: 0, units: 0, margin: 0 },
      profit30: Array(30).fill(0),
      sales30: Array(30).fill(0),
      topProducts: [],
      alerts: [],
    },

    deals: {
      monitors: [
        { id: "hukd", name: "HUKD Hot Deals", source: "Every 5 min · resale filter", status: "ok", lastRun: "1 min ago", leadsToday: 4, avgRoi: 25, hitRate: "5.0%" },
        { id: "dbh", name: "DBH Deals", source: "New-lead notifier", status: "warn", lastRun: "40 min ago", leadsToday: 1, avgRoi: 30, hitRate: "—" },
      ],
      leads: [
        { time: "21:04", source: "HUKD", title: "Demo product A (cordless vacuum)", buy: 100.0, sell: 150.0, profit: 20.0, roi: 20, bsr: "1,000" },
        { time: "20:51", source: "HUKD", title: "Demo product B (building set)", buy: 50.0, sell: 80.0, profit: 12.5, roi: 25, bsr: "500" },
        { time: "20:12", source: "DBH", title: "Demo product C (electric toothbrush)", buy: 40.0, sell: 70.0, profit: 15.0, roi: 37, bsr: "750" },
      ],
      leads7: series(7, 10, 6, 0.5),
    },

    jobs: {
      pipeline: [
        { label: "Scraped", n: 100 },
        { label: "Matched", n: 20 },
        { label: "Applied", n: 10 },
        { label: "Interview", n: 2 },
        { label: "Offer", n: 0 },
      ],
      appliedThisWeek: 3,
      matches: [
        { title: "Example Role One", company: "Example Co", location: "London · Hybrid", salary: "£30k", rating: 90, posted: "Today" },
        { title: "Example Role Two", company: "Sample Ltd", location: "Remote UK", salary: "£28k", rating: 82, posted: "1d" },
      ],
      followUps: [
        { company: "Example Co", role: "Example Role One", due: "Today", stage: "Applied 7 days ago" },
      ],
    },

    isa: {
      provider: "Stocks & Shares ISA",
      value: 10000.0,
      invested: 9500.0,
      dayChange: 25.0,
      dayChangePct: 0.25,
      allowance: 20000,
      contributedThisYear: 2000,
      taxYearEnd: "5 Apr 2027",
      history: series(26, 9000, 200, 40),
      holdings: [
        { ticker: "ETF1", name: "Global equity ETF (demo)", value: 6000.0, cost: 5600, weight: 60, day: 0.3 },
        { ticker: "ETF2", name: "US equity ETF (demo)", value: 3000.0, cost: 2900, weight: 30, day: 0.2 },
        { ticker: "CASH", name: "Uninvested cash", value: 1000.0, cost: 1000, weight: 10, day: 0 },
      ],
      watchlist: [],
    },

    calendar: [
      // day offset from today, time, title, kind
      { d: 0, t: "10:00", title: "Demo: send inbound shipment", kind: "fba" },
      { d: 1, t: "14:00", title: "Demo: supplier call", kind: "fba" },
      { d: 2, t: "09:00", title: "Demo: personal appointment", kind: "life" },
    ],

    agents: [
      { name: "HUKD monitor", kind: "Local service", schedule: "Every 5 min", status: "ok", last: "1 min ago" },
      { name: "DBH leads notifier", kind: "Local service", schedule: "Every 10 min", status: "warn", last: "40 min ago" },
      { name: "Command Centre watchdog", kind: "Scheduled task", schedule: "Every 5 min", status: "ok", last: "2 min ago" },
    ],

    notes: [
      { title: "Welcome to the Memory page", type: "reference", updated: "Today", body: "This page shows sample notes. Replace them with your own project notes." },
      { title: "Example project note", type: "project", updated: "Today", body: "Short summary of a project, its status and where its files live." },
    ],

    feed: [
      { icon: "bolt", tint: "green", title: "New lead: demo product B, 25% ROI", meta: "HUKD monitor · 20:51" },
      { icon: "clock", tint: "amber", title: "DBH notifier hasn't checked in for 40 min", meta: "System · 20:25" },
    ],
  };
})();
