(() => {
  const D = window.DATA;
  const $ = (s, el = document) => el.querySelector(s);

  // ---------- Formatting ----------
  const gbp = (n, dp = 2) => n === null || n === undefined ? "—" : "£" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: dp, maximumFractionDigits: dp });
  const pct = (n) => (n > 0 ? "+" : "") + n.toFixed(1) + "%";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  // ---------- Icons ----------
  const I = {
    home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
    box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
    chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    note: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    pound: '<path d="M17 20H7c2-2 2-5 2-8V8a4 4 0 0 1 7-2.5M6 13h8"/>',
    alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    trend: '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    cart: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.6L21 7H6"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    play: '<path d="m7 4 13 8-13 8z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  };
  const icon = (n) => `<svg viewBox="0 0 24 24">${I[n] || ""}</svg>`;

  // ---------- Navigation ----------
  const NAV = [
    { id: "overview", label: "Overview", icon: "home" },
    { section: "Business" },
    { id: "fba", label: "Sales", icon: "box" },
    { id: "purchases", label: "Purchases", icon: "cart", count: "…" },
    { id: "money", label: "Money", icon: "pound" },
    { id: "insights", label: "Insights", icon: "trend", count: "…" },
    { id: "claims", label: "Claims & Leaks", icon: "shield", count: "…" },
    { id: "deals", label: "Deal Monitors", icon: "bolt", count: D.deals.monitors.reduce((a, m) => a + m.leadsToday, 0) },
    { section: "Personal" },
    { id: "important", label: "Important", icon: "alert", count: "…" },
    { id: "jobs", label: "Job Hunt", icon: "briefcase", count: D.jobs.matches.length },
    { id: "isa", label: "Stocks & Shares ISA", icon: "chart" },
    { id: "calendar", label: "Calendar", icon: "calendar" },
    { section: "System" },
    { id: "agents", label: "Agents", icon: "cpu" },
    { id: "memory", label: "Memory", icon: "note" },
  ];

  function renderNav(active) {
    if ($("#nav").children.length) {
      document.querySelectorAll(".nav-item").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + active));
      return moveGlider();
    }
    $("#nav").innerHTML = '<div class="nav-glider" id="glider"></div>' + NAV.map((n) =>
      n.section
        ? `<div class="nav-label">${n.section}</div>`
        : `<a class="nav-item ${n.id === active ? "active" : ""}" href="#${n.id}">${icon(n.icon)}<span>${n.label}</span>${n.count ? `<span class="count">${n.count}</span>` : ""}</a>`
    ).join("");
    moveGlider(true);
  }
  function moveGlider(instant) {
    const a = $(".nav-item.active"), g = $("#glider");
    if (!a || !g) return;
    if (instant) g.style.transition = "none";
    g.style.transform = `translateY(${a.offsetTop}px)`;
    g.style.height = a.offsetHeight + "px";
    g.style.opacity = 1;
    if (instant) requestAnimationFrame(() => (g.style.transition = ""));
  }

  // ---------- Charts (inline SVG) ----------
  // Charts are drawn after layout so they render at the container's real pixel width
  const charts = [];
  const deferred = (draw) => `<div class="chart" data-cid="${charts.push(draw) - 1}"></div>`;
  function drawCharts() {
    document.querySelectorAll(".chart[data-cid]").forEach((el) => {
      const w = Math.max(200, el.clientWidth);
      el.innerHTML = charts[el.dataset.cid](w);
    });
  }

  function areaChart(values, opts = {}) {
    if (values.length === 1) {
      values = [values[0], values[0]];
      if (opts.labels) opts = { ...opts, labels: [opts.labels[0], opts.labels[0]] };
      if (opts.overlay) opts = { ...opts, overlay: { ...opts.overlay, values: [opts.overlay.values[0], opts.overlay.values[0]] } };
    }
    if (!values.length) values = [0, 0];
    return deferred((w) => areaSvg(values, w, opts));
  }

  function areaSvg(values, w, { h = 220, color = "--accent", labels, fmt = (v) => v, bare = false, name, overlay, fitMin = false, id = "c" + Math.random().toString(36).slice(2, 7) } = {}) {
    const labelW = String(fmt(Math.round(Math.max(...values, ...(overlay ? overlay.values : []))))).length * 7 + 12;
    const pad = bare ? { t: 16, r: 0, b: 0, l: 0 } : { t: 10, r: 8, b: 26, l: Math.max(44, labelW) };
    const all = overlay ? values.concat(overlay.values) : values;
    const lo = Math.min(...all), hi = Math.max(...all);
    const max = fitMin ? hi + (hi - lo) * 0.12 : (hi || 1) * 1.12;
    const min = fitMin ? Math.max(0, lo - (hi - lo) * 0.15) : Math.min(0, lo);
    const x = (i) => pad.l + (i * (w - pad.l - pad.r)) / (values.length - 1);
    const y = (v) => pad.t + (1 - (v - min) / (max - min)) * (h - pad.t - pad.b);
    const pts = values.map((v, i) => [x(i), y(v)]);
    const curve = (pp) => pp.map((p, i) => {
      if (!i) return `M${p[0]},${p[1]}`;
      const [px, py] = pp[i - 1], cx = (px + p[0]) / 2;
      return `C${cx},${py} ${cx},${p[1]} ${p[0]},${p[1]}`;
    }).join(" ");
    const line = curve(pts);
    const opts2 = overlay ? { pts: overlay.values.map((v, i) => [x(i), y(v)]), c: css(overlay.color || "--blue") } : null;
    const c = css(color), grid = css("--border-soft"), muted = css("--muted");
    const ticks = 4;
    let g = "";
    for (let k = 0; k <= ticks && !bare; k++) {
      const v = min + ((max - min) * k) / ticks, yy = y(v);
      g += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${yy}" y2="${yy}" stroke="${grid}" stroke-width="1"/>`;
      g += `<text x="${pad.l - 8}" y="${yy + 4}" fill="${muted}" font-size="11" text-anchor="end">${fmt(Math.round(v))}</text>`;
    }
    if (labels && !bare) {
      const step = Math.ceil(labels.length / 6);
      labels.forEach((l, i) => {
        if (i % step === 0 || i === labels.length - 1)
          g += `<text x="${x(i)}" y="${h - 6}" fill="${muted}" font-size="11" text-anchor="${i === labels.length - 1 ? "end" : i === 0 ? "start" : "middle"}">${l}</text>`;
      });
    }
    const tipFor = (i) => (labels ? labels[i] + " · " : "") +
      (overlay ? `${overlay.name}: ${fmt(overlay.values[i])} · ${name}: ${fmt(values[i])}` : fmt(values[i]));
    const hits = pts.map((p, i) =>
      `<rect x="${p[0] - (w / values.length) / 2}" y="0" width="${w / values.length}" height="${h}" fill="transparent" data-tip="${esc(tipFor(i))}" data-x="${p[0]}" data-y="${p[1]}"${opts2 ? ` data-y2="${opts2.pts[i][1]}"` : ""}/>`
    ).join("");
    const over = opts2 ? `
      <defs><linearGradient id="o${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${opts2.c}" stop-opacity=".16"/><stop offset="1" stop-color="${opts2.c}" stop-opacity="0"/></linearGradient></defs>
      <path class="fill-in" d="${curve(opts2.pts)} L${opts2.pts.at(-1)[0]},${h - pad.b} L${opts2.pts[0][0]},${h - pad.b} Z" fill="url(#o${id})"/>
      <path class="draw" pathLength="1" d="${curve(opts2.pts)}" stroke="${opts2.c}" stroke-width="1.8" fill="none" opacity=".9"/>
      <circle class="hover-dot hover-dot-2" r="4" fill="${opts2.c}" stroke="${css("--panel-solid")}" stroke-width="2" opacity="0"/>` : "";
    return `<svg viewBox="0 0 ${w} ${h}" style="width:${w}px;height:${h}px">
      <defs><linearGradient id="g${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${c}" stop-opacity="${bare ? ".38" : ".28"}"/><stop offset="1" stop-color="${c}" stop-opacity="0"/></linearGradient></defs>
      ${g}
      ${over}
      <path class="fill-in" d="${line} L${pts.at(-1)[0]},${h - pad.b} L${pts[0][0]},${h - pad.b} Z" fill="url(#g${id})"/>
      <filter id="f${id}"><feGaussianBlur stdDeviation="5"/></filter>
      <path class="draw" pathLength="1" d="${line}" stroke="${c}" stroke-width="3" fill="none" opacity=".55" filter="url(#f${id})"/>
      <path class="draw" pathLength="1" d="${line}" stroke="${c}" stroke-width="2.2" fill="none"/>
      <circle class="hover-dot" r="4.5" fill="${c}" stroke="${css("--panel-solid")}" stroke-width="2" opacity="0"/>
      ${hits}
    </svg>`;
  }

  function barChart(values, labels, opts = {}) {
    return deferred((w) => barSvg(values, labels, w, opts));
  }

  function barSvg(values, labels, w, { h = 150, color = "--accent", unit = "leads", every = 1 } = {}) {
    const pad = { t: 8, b: 24 }, max = Math.max(...values) * 1.1;
    const bw = (w / values.length) * 0.56;
    const c = css(color), muted = css("--muted");
    const bars = values.map((v, i) => {
      const cx = (w / values.length) * (i + 0.5), bh = (v / max) * (h - pad.t - pad.b);
      return `<rect class="bar" style="animation-delay:${i * 60 + 150}ms" x="${cx - bw / 2}" y="${h - pad.b - bh}" width="${bw}" height="${bh}" rx="5" fill="${c}" opacity="${i === values.length - 1 ? 1 : 0.45}" data-tip="${labels[i]} · ${v} ${unit}"/>
              ${i % every === every - 1 || i === values.length - 1 ? `<text x="${cx}" y="${h - 6}" fill="${muted}" font-size="11" text-anchor="${i === values.length - 1 ? "end" : "middle"}">${labels[i]}</text>` : ""}`;
    }).join("");
    return `<svg viewBox="0 0 ${w} ${h}" style="width:${w}px;height:${h}px">${bars}</svg>`;
  }

  function sparkline(values, color = "--accent", w = 120, h = 36) {
    const max = Math.max(...values), min = Math.min(...values);
    const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 3 - ((v - min) / (max - min || 1)) * (h - 6)}`).join(" ");
    return `<svg viewBox="0 0 ${w} ${h}" style="width:${w}px;height:${h}px"><polyline points="${pts}" fill="none" stroke="${css(color)}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
  }

  function donut(items, size = 170) {
    const r = 64, cxy = size / 2, circ = 2 * Math.PI * r;
    let off = 0;
    const arcs = items.map((it) => {
      const len = (it.weight / 100) * circ;
      const s = `<circle cx="${cxy}" cy="${cxy}" r="${r}" fill="none" stroke="${it.color.startsWith("--") ? css(it.color) : it.color}" stroke-width="18" stroke-dasharray="${Math.max(0.6, len - 2)} ${circ - Math.max(0.6, len - 2)}" stroke-dashoffset="${-off}" transform="rotate(-90 ${cxy} ${cxy})" data-tip="${it.label} · ${it.weight}%"/>`;
      off += len;
      return s;
    }).join("");
    return `<svg viewBox="0 0 ${size} ${size}" style="width:${size}px;height:${size}px">${arcs}</svg>`;
  }

  // Tooltips + hover dot for every chart on the page
  const tip = document.createElement("div");
  tip.className = "tooltip";
  document.body.appendChild(tip);
  document.addEventListener("mousemove", (e) => {
    const t = e.target.closest("[data-tip]");
    document.querySelectorAll(".hover-dot").forEach((d) => d.setAttribute("opacity", 0));
    if (!t) { tip.style.opacity = 0; return; }
    tip.textContent = t.dataset.tip;
    tip.style.opacity = 1;
    tip.style.left = e.clientX + 12 + "px";
    tip.style.top = e.clientY - 34 + "px";
    if (t.dataset.x) {
      const dot2 = t.closest("svg").querySelector(".hover-dot-2");
      if (dot2 && t.dataset.y2) { dot2.setAttribute("cx", t.dataset.x); dot2.setAttribute("cy", t.dataset.y2); dot2.setAttribute("opacity", 1); }
      const dot = t.closest("svg").querySelector(".hover-dot:not(.hover-dot-2)");
      dot.setAttribute("cx", t.dataset.x);
      dot.setAttribute("cy", t.dataset.y);
      dot.setAttribute("opacity", 1);
    }
  });

  // ---------- Shared bits ----------
  const dayLabels = (n) => Array.from({ length: n }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (n - 1 - i));
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  });
  const weekdayLabels = (n) => Array.from({ length: n }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (n - 1 - i));
    return i === n - 1 ? "Today" : d.toLocaleDateString("en-GB", { weekday: "short" });
  });

  const kpi = ({ label, value, delta, foot, ic, tint = "accent", spark }) => `
    <div class="card kpi">
      <div class="kpi-label"><span class="kpi-icon tint-${tint}">${icon(ic)}</span>${label}</div>
      <div class="row-flex" style="justify-content:space-between;align-items:flex-end">
        <div class="kpi-value">${value}</div>${spark || ""}
      </div>
      <div class="kpi-foot">${delta !== undefined ? `<span class="delta ${delta >= 0 ? "up" : "down"}">${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(1)}%</span>` : "<span></span>"}<span>${foot || ""}</span></div>
    </div>`;

  const statusChip = (s) => ({
    ok: '<span class="chip tint-green"><span class="dot ok" style="box-shadow:none;width:6px;height:6px"></span>Running</span>',
    warn: '<span class="chip tint-amber"><span class="dot warn" style="box-shadow:none;width:6px;height:6px"></span>Delayed</span>',
    err: '<span class="chip tint-red">Stopped</span>',
    idle: '<span class="chip" style="background:var(--panel-2);color:var(--text-2)">Idle</span>',
  }[s]);

  const sourceTint = { Argos: "red", "TK Maxx": "accent", HUKD: "amber", DBH: "green", Currys: "blue", Discord: "accent" };
  const kindColor = { fba: "--accent", job: "--green", life: "--amber" };
  const roiChip = (r) => r === null || r === undefined ? '<span class="cell-sub">—</span>' : `<span class="chip tint-${r >= 30 ? "green" : r >= 15 ? "blue" : "amber"}">${r}%</span>`;
  const initials = (s) => s.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

  const pageHead = (title, sub, actions = "") =>
    `<div class="page-head"><div><h1>${title}</h1><p>${sub}</p></div><div class="actions">${actions}</div></div>`;

  function greeting() {
    const h = new Date().getHours();
    return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  }

  const URGENT_EV = /deadline|due\b|asap|to do|assessment|online test|interview|collect|expires?/i;
  function agenda(items) {
    if (!items.length) return `<div class="empty">Nothing scheduled</div>`;
    return `<div class="list">${items.map((e) => `
      <div class="list-item ${e.d === 0 && URGENT_EV.test(e.title) ? "urgent" : ""}">
        <span class="agenda-time">${e.t}</span>
        <span class="agenda-bar" style="background:var(${kindColor[e.kind]})"></span>
        <div class="list-body"><div class="list-title">${esc(e.title)}</div><div class="list-meta">${{ fba: "Business", job: "Job hunt", life: "Personal" }[e.kind]}${e.end ? " · until " + e.end : ""}${e.location ? " · " + esc(e.location) : ""}</div></div>
      </div>`).join("")}</div>`;
  }

  const STATUS_LABEL = { bought: "✅ Bought", declined: "✕ Declined", oos: "⌀ Out of stock" };
  function leadsTable(leads, limit, opts = {}) {
    const when = (l) => l.time && l.time.includes("T") ? relTime(l.time) : l.time;
    const posted = (l) => l.postedAt ? new Date(l.postedAt).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
    const mainLabel = (u) => u.includes("amazon.co.uk") ? "Amazon" : u.includes("dbhdeals") ? "DBH lead" : u.includes("hotukdeals") ? "HUKD" : "Open";
    const linkSet = (l) => [
      l.url ? `<a class="link" href="${esc(l.url)}" target="_blank" rel="noopener">${mainLabel(l.url)}</a>` : "",
      l.supplierUrl ? `<a class="link" href="${esc(l.supplierUrl)}" target="_blank" rel="noopener">Supplier${l.store ? " (" + esc(l.store) + ")" : ""}</a>` : "",
      (l.sasUrl || l.asin) ? `<a class="link" href="${esc(l.sasUrl || "https://sas.selleramp.com/sas/lookup?SasLookup%5Bsearch_term%5D=" + l.asin)}" target="_blank" rel="noopener">SAS</a>` : "",
      l.keepa ? `<a class="link" href="${esc(l.keepa)}" target="_blank" rel="noopener">Keepa</a>` : "",
      l.discordUrl ? `<a class="link" href="${esc(l.discordUrl)}" target="_blank" rel="noopener">Discord post</a>` : "",
    ].filter(Boolean).join(" · ");
    const statusTint = (s) => s === "bought" ? "green" : s === "oos" ? "amber" : "red";
    const actions = (l) => {
      if (!opts.actions || !l.key) return "";
      if (l.status) return `<div class="lead-actions"><span class="chip tint-${statusTint(l.status)}">${STATUS_LABEL[l.status]}</span><button class="mini-btn" data-lead-status="active" data-key="${esc(l.key)}">↩ Back to leads</button></div>`;
      return `<div class="lead-actions"><button class="mini-btn ok" data-lead-status="bought" data-key="${esc(l.key)}">✅ Bought</button><button class="mini-btn no" data-lead-status="declined" data-key="${esc(l.key)}">✕ Declined</button><button class="mini-btn oos" data-lead-status="oos" data-key="${esc(l.key)}">⌀ OOS</button></div>`;
    };
    return `<div class="table-wrap"><table>
      <thead><tr><th>Product</th><th>Source</th><th class="num">Buy</th><th class="num">Sell</th><th class="num">Profit</th><th class="num">ROI</th><th class="num">When</th>${opts.actions ? '<th class="num"></th>' : ""}</tr></thead>
      <tbody>${leads.slice(0, limit).map((l) => {
        const suspect = l.roi != null && l.roi > 300;
        const meta = [l.tag, l.spm ? l.spm + "/mo" : "", l.via && l.via !== l.tag && l.via !== "DBH" && l.source !== "Discord" ? l.via : ""].filter(Boolean).join(" · ");
        return `
        <tr class="lead-row">
          <td>${l.topPick ? `<span class="chip tint-green top-pick" title="${esc(l.pickWhy || "Matches what you usually buy")}">★ Top pick</span> ` : ""}<div class="cell-main" style="max-width:340px;overflow:hidden;text-overflow:ellipsis">${esc(l.title)}</div>
            <div class="cell-sub">${esc(meta)}</div>
            <div class="cell-sub lead-links">${linkSet(l)}</div></td>
          <td><span class="chip tint-${sourceTint[l.source] || "blue"}">${esc(l.source)}</span></td>
          <td class="num">${l.buy != null ? gbp(l.buy) : "—"}${l.was ? `<div class="cell-sub" style="text-decoration:line-through">${gbp(l.was)}</div>` : ""}</td>
          <td class="num">${l.sell != null ? gbp(l.sell) : "—"}</td>
          <td class="num ${l.profit != null && l.profit < 0 ? "down" : "up"}" style="font-weight:600">${l.profit != null ? gbp(l.profit) : "—"}</td>
          <td class="num">${l.roi != null ? (suspect ? `<span class="chip tint-red" title="ROI this high usually means a wrong Amazon match">${l.roi}% · check match</span>` : roiChip(l.roi)) : "—"}</td>
          <td class="num cell-sub">${esc(when(l) || "")}${l.postedAt ? `<div class="cell-sub" title="Posted on Discord">Posted ${esc(posted(l))}</div>` : ""}</td>
          ${opts.actions ? `<td class="num">${actions(l)}</td>` : ""}
        </tr>`;
      }).join("")}</tbody></table></div>`;
  }

  // ---------- Views ----------
  // ---------- AI brief (overview) ----------
  function aiBrief() {
    const L = [];
    const b = (x) => `<b>${x}</b>`;
    if (D.fbaLive) L.push(["fba", `Sales today: ${b(gbp(D.fba.today.profit))} profit on ${b(D.fba.today.units ?? 0)} units, ${b(gbp(D.fba.month.profit))} so far this month.`]);
    else if (D.fbaStatus && D.fbaStatus.needsLogin) L.push(["warn", `Sales feed offline. Invenno needs you to log in again (connect-invenno.bat).`]);
    try {
      const open = D.dealsLive ? D.deals.leads.filter((l) => isProfitLead(l) && !l.status) : [];
      if (open.length) L.push(["deals", `${b(open.length)} open profit leads waiting for a decision.`]);
    } catch {}
    try {
      if (D.important && D.important.configured) {
        const hi = impItems().filter((x) => x.priority === 1);
        L.push([hi.length ? "warn" : "ok", hi.length ? `${b(hi.length)} high-priority emails need attention: ${esc(hi[0].subject.slice(0, 60))}.` : "No high-priority emails right now."]);
      }
    } catch {}
    const codes = (D.otp.codes || []).filter((c) => c.today);
    if (codes.length) L.push(["warn", `${b(codes.length)} delivery code${codes.length > 1 ? "s" : ""} arrived today.`]);
    const now = new Date(), hm = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const nextEv = (D.calendar || []).filter((e) => e.d === 0 && (!e.t || e.t >= hm))[0] || (D.calendar || []).find((e) => e.d === 1);
    if (nextEv) L.push(["cal", `Next up: ${b(esc(nextEv.title))}${nextEv.t ? " at " + nextEv.t : ""}${nextEv.d === 1 ? " tomorrow" : ""}.`]);
    if (D.reclaim && D.reclaim.configured && D.reclaim.dashboard && D.reclaim.dashboard.atRisk14) L.push(["warn", `${b(gbp(D.reclaim.dashboard.atRisk14))} in claims hits its deadline within 14 days.`]);
    if (D.isaLive) L.push(["ok", `ISA at ${b(gbp(D.isa.value))}, ${D.isa.dayChangePct >= 0 ? "up" : "down"} ${Math.abs(D.isa.dayChangePct).toFixed(2)}% today.`]);
    if (!L.length) L.push(["ok", "All systems nominal. Waiting for live data…"]);
    return `
      <div class="card ai-brief span-12">
        <div class="ai-orb"><i></i><i></i><i></i></div>
        <div class="brief-body">
          <div class="brief-head"><span class="eyebrow">AI brief</span><span class="brief-status"><span class="dot ok"></span>analysing ${L.length} signals</span></div>
          ${L.slice(0, 6).map(([k, t]) => `<div class="brief-line k-${k}"><span class="brief-dot"></span><span class="brief-text">${t}</span></div>`).join("")}
        </div>
      </div>`;
  }

  const views = {};

  // Selected-range figures, falling back to month-to-date until the first range load finishes
  function rangeNow() {
    const rd = D.rangeData && D.rangeData.current ? D.rangeData : null;
    const f = D.fba;
    const rc = rd ? rd.current : D.range.label === "Today" ? f.today : { profit: f.month.profit, sales: f.month.sales, units: f.month.units, margin: f.month.margin ?? f.today.margin, roi: f.month.roi };
    return { rd, rc };
  }
  const deltaSpan = (n) => n === null || n === undefined ? "" :
    `<span class="delta ${n >= 0 ? "up" : "down"}">${n >= 0 ? "▲" : "▼"} ${Math.abs(n).toFixed(1)}% vs previous period</span>`;

  views.overview = () => {
    const { rd, rc } = rangeNow();
    const f = D.fba, isaGain = D.isa.value - D.isa.invested;
    const today = D.calendar.filter((e) => e.d === 0);
    const leadsToday = D.deals.monitors.reduce((a, m) => a + m.leadsToday, 0);
    const running = D.agents.filter((a) => a.status === "ok").length;
    const dateStr = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
    const mini = (ic, tint, label, value, sub, spark) => `
      <div class="card mini">
        <span class="kpi-icon tint-${tint}">${icon(ic)}</span>
        <div class="list-body"><div class="card-sub">${label}</div><div class="kpi-value">${value}</div><div class="card-sub">${sub}</div></div>
        ${spark || ""}
      </div>`;
    return `
      ${pageHead(`${greeting()}${D.user.name ? ", " + D.user.name : ""}`, `${dateStr} · ${running} of ${D.agents.length} agents running`,
        `<button class="btn" id="openPalette">${icon("bolt")}Quick jump <kbd style="margin-left:4px">Ctrl K</kbd></button>`)}
      ${(D.otp.codes || []).some((c) => c.today) ? `
      <div class="card otp-banner" style="margin-bottom:16px">
        <div class="card-head"><div><div class="card-title">📦 Delivery codes today</div><div class="card-sub">Paste prep codes into your prep Discord ticket</div></div><a class="link" href="#important">All codes</a></div>
        ${otpCards(D.otp.codes.filter((c) => c.today), true)}
      </div>` : ""}
      <div class="grid">
        ${aiBrief()}
        ${new Date().getDay() === 1 && D.insights && D.insights.digest ? digestCard(D.insights.digest, true) : ""}
        ${recapCard()}
        <div class="card hero span-8 range-scope ${D.rangeLoading ? "is-loading" : ""}">
          <div class="hero-glow"></div>
          <div class="hero-top">
            <div>
              <div class="hero-label"><span class="dot ok"></span>Sales · ${esc(D.range.label)}</div>
              <div class="hero-figures">
                <div><div class="hero-cap"><i style="background:var(--accent)"></i>Profit</div><div class="hero-value">${gbp(rc.profit)}</div></div>
                <div><div class="hero-cap"><i style="background:var(--blue)"></i>Sales</div><div class="hero-value hero-value-2">${gbp(rc.sales)}</div></div>
              </div>
              <div class="hero-meta">
                ${rd && rd.change.profit != null ? `<span>Profit ${deltaSpan(rd.change.profit).replace(" vs previous period", "")}</span>` : ""}
                ${rd && rd.change.sales != null ? `<span>Sales ${deltaSpan(rd.change.sales).replace(" vs previous period", "")}</span>` : ""}
                ${rd ? `<span class="cell-sub">vs previous period</span>` : ""}
                <span>Units <b>${rc.units ?? "—"}</b></span>
                <span>Margin <b>${rc.margin != null ? Number(rc.margin).toFixed(1) + "%" : "—"}</b></span>
                <span>ROI <b>${rc.roi != null ? Number(rc.roi).toFixed(1) + "%" : "—"}</b></span>
              </div>
            </div>
            ${rangeButton()}
          </div>
          ${D.rangeError || D.fbaStatus.needsLogin ? `<div class="banner" style="margin:14px 0 0">${icon("alert")}<span>${D.fbaStatus.needsLogin ? (D.fbaStatus.stale ? `Invenno login expired, so these are your last saved figures (${esc(D.fbaStatus.updated || "")}), not live. ` : "Invenno login expired, so no figures to show. ") + "Double-click connect-invenno.bat to log in again." : esc(D.rangeError)}</span></div>` : ""}
          ${areaChart(rd ? rd.profit : f.profit30, { labels: rd ? rd.labels : f.labels || dayLabels(30), fmt: (v) => "£" + v.toLocaleString("en-GB"), h: 190, bare: true,
            name: "Profit", overlay: { values: rd ? rd.sales : f.sales30, color: "--blue", name: "Sales" } })}
        </div>

        <div class="stack span-4">
          ${mini("chart", "blue", "Stocks & Shares ISA", gbp(D.isa.value), `<span class="delta ${D.isa.dayChangePct >= 0 ? "up" : "down"}">${D.isa.dayChangePct >= 0 ? "▲" : "▼"} ${Math.abs(D.isa.dayChangePct).toFixed(2)}%</span> today · ${D.isa.return != null ? gbp(D.isa.return, 0) + " return" : gbp(isaGain, 0) + " gain"}`, sparkline(D.isa.history.slice(-60), "--blue", 80, 34))}
          ${D.dealsLive
            ? mini("bolt", "amber", "Deal leads today", D.deals.profitToday, `${D.deals.totals.running}/${D.deals.totals.count} monitors running · ${D.deals.monitors.find((m) => m.id === "hukd")?.leadsToday ?? 0} HUKD posts`, sparkline(D.deals.leads7, "--amber", 80, 34))
            : mini("bolt", "amber", "Deal leads today", leadsToday, `${D.deals.monitors.filter((m) => m.status === "ok").length} monitors live`, sparkline(D.deals.leads7, "--amber", 80, 34))}
          ${D.jobsLive
            ? mini("briefcase", "green", "Job hunt", `${D.jobs.counts.goodWeek} top matches`, `${D.jobs.counts.appliedWeek} applied this week · ${D.jobs.inProcess.length} in process`)
            : mini("briefcase", "green", "Job hunt", `${D.jobs.matches.length} new matches`, `${D.jobs.appliedThisWeek} applied this week · ${D.jobs.followUps.length} follow-ups`)}
        </div>

        <div class="card flush span-8">
          <div class="card-head"><div><div class="card-title">Latest deal leads</div><div class="card-sub">DBH · Discord</div></div><a class="link" href="#deals">View all</a></div>
          <div style="margin-top:8px">${leadsTable(D.dealsLive ? D.deals.leads.filter((l) => isProfitLead(l) && !l.status) : D.deals.leads, 6)}</div>
        </div>

        <div class="card span-4">
          <div class="card-head"><div class="card-title">Today</div><a class="link" href="#calendar">Calendar</a></div>
          ${agenda(today)}
        </div>

        <div class="card span-6">
          <div class="card-head"><div><div class="card-title">Deadline radar</div><div class="card-sub">${D.reclaim && D.reclaim.configured && D.reclaim.dashboard ? `${gbp(D.reclaim.dashboard.atRisk14)} at risk · ${gbp(D.reclaim.dashboard.leakShortfall)} in leaks` : "ReclaimHQ claims & deadlines"}</div></div><a class="link" href="#claims">All claims</a></div>
          ${D.reclaim && D.reclaim.configured ? actionList(actionItems(), 5) : reclaimBanner()}
        </div>

        <div class="card span-6">
          <div class="card-head"><div><div class="card-title">Important emails</div><div class="card-sub">${D.important && D.important.configured ? `${impItems().filter((x) => x.priority === 1).length} high priority` : "Gmail"}</div></div><a class="link" href="#important">Open</a></div>
          ${D.important && D.important.configured
            ? (impItems().length ? `<div class="list">${impItems().slice(0, 5).map((x) => `
              <a class="list-item action-item ${x.priority === 1 && x.unread ? "urgent" : ""}" href="${esc(x.url)}" target="_blank" rel="noopener">
                <span class="kpi-icon tint-${prioTint[x.priority]}">${icon(catIcon[x.category] || "alert")}</span>
                <div class="list-body"><div class="list-title">${x.unread ? "● " : ""}${esc(x.subject)}${x.count > 1 ? ` <span class="cell-sub">×${x.count}</span>` : ""}</div><div class="list-meta">${esc(x.reason)} · ${esc(x.from)}</div></div>
                <div class="list-right cell-sub">${relTime(x.received)}</div></a>`).join("")}</div>` : `<div class="empty">Nothing important ✓</div>`)
            : `<div class="banner" style="margin:0">${icon("alert")}<span>Add a Gmail app password to switch this on — see the Important page.</span></div>`}
        </div>

        <div class="card span-12">
          <div class="card-head"><div class="card-title">Job pipeline</div><a class="link" href="#jobs">Open</a></div>
          ${pipeline()}
        </div>
      </div>`;
  };

  function pipeline() {
    const top = Math.max(1, ...D.jobs.pipeline.map((s) => s.n));
    return `<div class="pipeline">${D.jobs.pipeline.map((s) => `
      <div class="stage"><div class="stage-n">${s.n.toLocaleString("en-GB")}</div><div class="stage-l">${s.label}</div>
      <div class="progress"><div style="width:${Math.max(3, (s.n / top) * 100)}%"></div></div></div>`).join("")}</div>`;
  }

  function fbaBanner() {
    const st = D.fbaStatus || {};
    if (st.loading || st.configured === null) return `<div class="banner ok">${icon("refresh")}Fetching your figures from Invenno…</div>`;
    if (st.needsLogin) return `<div class="banner">${icon("alert")}<span>Invenno login expired${st.stale ? `, so these are your <b>last saved figures</b> (${esc(st.updated || "")}), not live` : ", so there are no figures to show"}. Double-click <code>connect-invenno.bat</code> in <code>Documents\\command-centre</code> and log in.</span></div>`;
    if (!st.configured) return `<div class="banner">${icon("alert")}<span>No Invenno figures yet. Connect Invenno once by double-clicking <code>connect-invenno.bat</code> in <code>Documents\\command-centre</code> and logging in.</span></div>`;
    return (st.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("");
  }

  const signed = (n) => n === null || n === undefined ? undefined : Number(n);

  views.fba = () => {
    const f = D.fba, m = f.month, y = f.yesterday || {}, inv = f.inventory || {};
    const { rd, rc } = rangeNow();
    const top = rd ? rd.topProducts : f.topProducts;
    const projPct = m.projectedProfit ? Math.min(100, (m.profit / m.projectedProfit) * 100) : null;
    const labels = f.labels || dayLabels(30);
    return `
      ${pageHead("Sales", D.fbaLive ? `Live from Invenno · Amazon + eBay · updated ${D.fbaStatus.updated}` : "Profit, sales and stock from Invenno.",
        `${rangeButton()}<button class="btn" id="fbaRefresh">${icon("refresh")}Refresh</button><a class="btn" href="https://app.invenno.co.uk/" target="_blank" rel="noopener">${icon("ext")}Open Invenno</a>`)}
      ${fbaBanner()}
      <div class="grid">
        ${(() => {
          // Every card follows the date picker (defaults to Today); pick "Yesterday" to see yesterday
          const ch = rd && rd.change ? rd.change : {}, lbl = esc(D.range.label);
          const card = (html) => `<div class="span-3 range-scope ${D.rangeLoading ? "is-loading" : ""}"><div class="range-dep">${html}</div></div>`;
          return card(kpi({ label: `Profit · ${lbl}`, value: gbp(rc.profit), delta: signed(ch.profit), foot: ch.profit != null ? "vs previous period" : "", ic: "pound", tint: "green" }))
            + card(kpi({ label: `Sales · ${lbl}`, value: gbp(rc.sales), delta: signed(ch.sales), foot: ch.sales != null ? "vs previous period" : "", ic: "chart", tint: "blue" }))
            + card(kpi({ label: `Units · ${lbl}`, value: rc.units ?? "—", delta: signed(ch.units), foot: rc.orders != null ? `${rc.orders} orders` : "", ic: "box", tint: "accent" }))
            + card(kpi({ label: `ROI · ${lbl}`, value: rc.roi != null ? Number(rc.roi).toFixed(1) + "%" : "—", foot: rc.margin != null ? `${Number(rc.margin).toFixed(1)}% margin` : "profit / cost", ic: "trend", tint: "amber" }));
        })()}

        <div class="card span-8 range-scope ${D.rangeLoading ? "is-loading" : ""}">
          ${D.rangeError && !D.fbaStatus.needsLogin ? `<div class="banner">${icon("alert")}<span>${esc(D.rangeError)}</span></div>` : ""}
          <div class="card-head">
            <div><div class="card-title">Sales vs profit</div><div class="card-sub range-dep">${esc(D.range.label)} · ${gbp(rc.sales, 0)} sales · ${gbp(rc.profit, 0)} profit ${deltaSpan(rd ? rd.change.profit : null)}</div></div>
            <div class="chart-legend"><span><i style="background:var(--accent)"></i>Sales</span><span><i style="background:var(--green)"></i>Profit</span></div>
          </div>
          ${areaChart(rd ? rd.sales : f.sales30, { labels: rd ? rd.labels : labels, fmt: (v) => "£" + v.toLocaleString("en-GB"), h: 160 })}
          <div style="height:10px"></div>
          ${areaChart(rd ? rd.profit : f.profit30, { labels: rd ? rd.labels : labels, fmt: (v) => "£" + v.toLocaleString("en-GB"), h: 120, color: "--green" })}
        </div>

        <div class="card span-4">
          <div class="card-head"><div class="card-title">Month projection</div><span class="card-sub">${new Date().toLocaleDateString("en-GB", { month: "long" })}</span></div>
          <div class="kpi-value">${gbp(m.profit, 0)} <span class="card-sub" style="font-size:14px;font-weight:500">/ ${m.projectedProfit ? gbp(m.projectedProfit, 0) : "—"} expected</span></div>
          <div class="progress" style="margin:12px 0 6px;height:8px"><div style="width:${projPct ?? 0}%"></div></div>
          <div class="card-sub">${m.projectedSales ? `On track for ${gbp(m.projectedSales, 0)} sales` : `${gbp(m.sales, 0)} sales so far`}</div>
          <div style="height:22px"></div>
          <div class="card-title" style="margin-bottom:12px">Stock on hand</div>
          <div class="monitor-stats">
            <div><b>${inv.units ?? "—"}</b><span>Units</span></div>
            <div><b>${inv.cost !== undefined ? gbp(inv.cost, 0) : "—"}</b><span>At cost</span></div>
            <div><b>${inv.profit !== undefined ? gbp(inv.profit, 0) : "—"}</b><span>Profit in stock</span></div>
          </div>
          ${f.alerts.length ? `<div style="height:20px"></div><div class="card-title" style="margin-bottom:12px">Needs attention</div>
          <div class="list">${f.alerts.map((a) => `
            <div class="list-item"><span class="dot ${{ red: "err", amber: "warn", green: "ok" }[a.type]}"></span>
            <div class="list-body"><div class="list-title" style="white-space:normal">${esc(a.title)}</div><div class="list-meta">${esc(a.meta)}</div></div></div>`).join("")}</div>` : ""}
        </div>

        <div class="card flush span-12">
          <div class="card-head"><div><div class="card-title">Top sellers</div><div class="card-sub">${esc(D.range.label)} · by profit</div></div></div>
          <div class="table-wrap" style="margin-top:8px"><table>
            <thead><tr><th>Product</th><th class="num">Units</th><th class="num">Sales</th><th class="num">Profit</th><th class="num">ROI</th><th class="num">Margin</th></tr></thead>
            <tbody>${top.length ? "" : `<tr><td colspan="6" class="cell-sub" style="text-align:center;padding:30px">No sales in this range</td></tr>`}${top.map((p, i) => `
              <tr>
                <td><div class="row-flex">${p.image ? `<img class="thumb" src="${esc(p.image)}" alt="" style="object-fit:contain;background:#fff;padding:2px">` : `<span class="thumb tint-${["accent", "blue", "amber", "green", "red"][i % 5]}">${initials(p.title)}</span>`}
                  <div><div class="cell-main" style="max-width:520px;overflow:hidden;text-overflow:ellipsis">${esc(p.title)}</div><div class="cell-sub mono">${p.asin}</div></div></div></td>
                <td class="num">${p.units}</td><td class="num">${gbp(p.sales)}</td>
                <td class="num ${p.profit < 0 ? "down" : "up"}" style="font-weight:600">${gbp(p.profit)}</td>
                <td class="num">${roiChip(p.roi)}</td>
                <td class="num cell-sub">${p.margin !== undefined && p.margin !== null ? Number(p.margin).toFixed(1) + "%" : "—"}</td>
              </tr>`).join("")}</tbody></table></div>
        </div>
      </div>`;
  };

  views.agents = () => `
    ${pageHead("Agents", "Every monitor, script and Claude routine in one place.",
      `<button class="btn primary">${icon("plus")}New routine</button>`)}
    <div class="card flush"><div class="table-wrap"><table>
      <thead><tr><th>Agent</th><th>Type</th><th>Schedule</th><th>Status</th><th class="num">Last run</th><th class="num"></th></tr></thead>
      <tbody>${D.agents.map((a) => `
        <tr>
          <td><div class="row-flex"><span class="kpi-icon tint-${a.kind === "Claude routine" ? "accent" : a.kind === "Local service" ? "amber" : "blue"}">${icon(a.kind === "Claude routine" ? "clock" : a.kind === "Local service" ? "bolt" : "cpu")}</span><span class="cell-main">${a.name}</span></div></td>
          <td class="cell-sub">${a.kind}</td><td>${a.schedule}</td><td>${statusChip(a.status)}</td>
          <td class="num cell-sub">${a.last}</td>
          <td class="num"><button class="btn" style="height:30px">${icon("play")}Run</button></td>
        </tr>`).join("")}</tbody></table></div></div>`;

  let activeNote = 0;
  views.memory = () => {
    const typeTint = { project: "accent", feedback: "amber", reference: "blue" };
    const n = D.notes[activeNote];
    return `
      ${pageHead("Memory", "What Claude remembers — the same notes as your Obsidian vault.",
        `<button class="btn">${icon("ext")}Open in Obsidian</button>`)}
      <div class="card flush notes">
        <div class="notes-list">${D.notes.map((x, i) => `
          <div class="note-item ${i === activeNote ? "active" : ""}" data-note="${i}">
            <div class="list-title">${esc(x.title)}</div>
            <div class="list-meta"><span class="chip tint-${typeTint[x.type]}" style="padding:0 6px">${x.type}</span> · ${x.updated}</div>
          </div>`).join("")}</div>
        <div class="note-body">
          <h2>${esc(n.title)}</h2>
          <div class="tags"><span class="chip tint-${typeTint[n.type]}">${n.type}</span><span class="chip" style="background:var(--panel-2);color:var(--text-2)">Updated ${n.updated}</span></div>
          <p>${esc(n.body)}</p>
        </div>
      </div>`;
  };

  // ---------- Date range picker (Invenno-style presets + calendar) ----------
  const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const parseYmd = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const dayOnly = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const sameDay = (a, b) => a && b && a.getTime() === b.getTime();
  const fmtShort = (d, withYear) => d.toLocaleDateString("en-GB", { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });

  const PRESETS = [
    ["today", "Today"], ["yesterday", "Yesterday"], ["7d", "Last 7 days"], ["30d", "Last 30 days"],
    ["thisMonth", "This month"], ["lastMonth", "Last month"], ["90d", "Last 3 months"], ["ytd", "Year to date"], ["12m", "Last 12 months"],
  ];
  function presetRange(key) {
    const t = dayOnly(new Date());
    switch (key) {
      case "today": return [t, t];
      case "yesterday": return [addDays(t, -1), addDays(t, -1)];
      case "7d": return [addDays(t, -6), t];
      case "30d": return [addDays(t, -29), t];
      case "thisMonth": return [new Date(t.getFullYear(), t.getMonth(), 1), t];
      case "lastMonth": return [new Date(t.getFullYear(), t.getMonth() - 1, 1), new Date(t.getFullYear(), t.getMonth(), 0)];
      case "90d": return [addDays(t, -89), t];
      case "ytd": return [new Date(t.getFullYear(), 0, 1), t];
      case "12m": return [addDays(t, -364), t];
    }
  }
  function rangeLabel(r) {
    if (r.key !== "custom") return PRESETS.find((p) => p[0] === r.key)[1];
    const a = parseYmd(r.from), b = parseYmd(r.to);
    if (r.from === r.to) return fmtShort(a, true);
    return `${fmtShort(a, a.getFullYear() !== b.getFullYear())} – ${fmtShort(b, true)}`;
  }
  function makeRange(key, from, to) {
    if (key !== "custom") [from, to] = presetRange(key);
    const r = { key, from: ymd(from), to: ymd(to) };
    r.label = rangeLabel(r);
    return r;
  }

  // Restore the last range (presets are recomputed so "Today" stays today)
  // Always open on Today; other ranges (e.g. Yesterday) only when picked
  D.range = makeRange("today");

  const chevron = '<svg class="chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>';
  const rangeButton = () => `<button class="drp-btn" data-drp>${icon("calendar")}<span>${esc(D.range.label)}</span>${chevron}</button>`;

  const drp = document.createElement("div");
  drp.className = "drp";
  document.body.appendChild(drp);
  let pick = null; // { start, end, view: first-of-month Date, anchor: button }

  function openPicker(btn) {
    const r = D.range;
    const start = parseYmd(r.from), end = parseYmd(r.to);
    pick = { start, end, view: new Date(end.getFullYear(), end.getMonth(), 1), anchor: btn };
    btn.classList.add("open");
    drawPicker();
    drp.classList.add("open");
    placePicker();
  }
  function closePicker() {
    drp.classList.remove("open");
    document.querySelectorAll(".drp-btn.open").forEach((b) => b.classList.remove("open"));
    pick = null;
  }
  function placePicker() {
    if (!pick) return;
    const b = pick.anchor.getBoundingClientRect(), w = drp.offsetWidth;
    drp.style.top = Math.min(b.bottom + 8, innerHeight - drp.offsetHeight - 8) + "px";
    drp.style.left = Math.max(8, Math.min(b.right - w, innerWidth - w - 8)) + "px";
  }
  function drawPicker() {
    const today = dayOnly(new Date()), v = pick.view;
    const first = new Date(v.getFullYear(), v.getMonth(), 1);
    const gridStart = addDays(first, -((first.getDay() + 6) % 7)); // weeks start Monday
    let days = "";
    for (let i = 0; i < 42; i++) {
      const d = addDays(gridStart, i);
      if (i >= 35 && d.getMonth() !== v.getMonth()) break;
      const s = pick.start, e = pick.end;
      const isStart = sameDay(d, s), isEnd = sameDay(d, e) || (isStart && !e);
      const inside = s && e && d > s && d < e;
      const cls = ["drp-day", d.getMonth() !== v.getMonth() && "out", sameDay(d, today) && "today", inside && "in",
        (isStart || isEnd) && "sel", isStart && "start", isEnd && "end", isStart && e && !sameDay(s, e) && "has-end"].filter(Boolean).join(" ");
      days += `<button class="${cls}" data-day="${ymd(d)}" ${d > today ? "disabled" : ""}>${d.getDate()}</button>`;
    }
    const nextDisabled = new Date(v.getFullYear(), v.getMonth() + 1, 1) > today;
    const text = pick.start ? (pick.end && !sameDay(pick.start, pick.end) ? `${fmtShort(pick.start, true)} → ${fmtShort(pick.end, true)}` : fmtShort(pick.start, true)) : "Pick a start date";
    drp.innerHTML = `
      <div class="drp-presets">${PRESETS.map(([k, l]) => `<button class="drp-preset ${D.range.key === k ? "on" : ""}" data-preset="${k}">${l}</button>`).join("")}</div>
      <div class="drp-cal">
        <div class="drp-head">
          <button class="drp-nav" data-nav="-1" aria-label="Previous month"><svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg></button>
          <b>${v.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}</b>
          <button class="drp-nav" data-nav="1" aria-label="Next month" ${nextDisabled ? "disabled" : ""}><svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg></button>
        </div>
        <div class="drp-grid">${["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => `<div class="drp-dow">${d}</div>`).join("")}${days}</div>
        <div class="drp-foot">
          <span class="drp-text">${text}</span>
          <button class="btn" data-drp-cancel>Cancel</button>
          <button class="btn primary" data-drp-apply ${pick.start ? "" : "disabled"}>Apply</button>
        </div>
      </div>`;
  }

  function applyRange(r) {
    D.range = r;
    try { localStorage.setItem("cc-range", JSON.stringify({ key: r.key, from: r.from, to: r.to })); } catch {}
    closePicker();
    loadRange();
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-drp]");
    if (btn) { e.stopPropagation(); return pick && pick.anchor === btn ? closePicker() : (closePicker(), openPicker(btn)); }
    if (!pick) return;
    if (!e.target.closest(".drp")) return closePicker();
    const preset = e.target.closest("[data-preset]");
    if (preset) return applyRange(makeRange(preset.dataset.preset));
    const nav = e.target.closest("[data-nav]");
    if (nav && !nav.disabled) { pick.view = new Date(pick.view.getFullYear(), pick.view.getMonth() + +nav.dataset.nav, 1); return drawPicker(); }
    const day = e.target.closest("[data-day]");
    if (day && !day.disabled) {
      const d = parseYmd(day.dataset.day);
      if (!pick.start || pick.end) { pick.start = d; pick.end = null; }
      else if (d < pick.start) { pick.end = pick.start; pick.start = d; }
      else pick.end = d;
      return drawPicker();
    }
    if (e.target.closest("[data-drp-cancel]")) return closePicker();
    if (e.target.closest("[data-drp-apply]") && pick.start) {
      return applyRange(makeRange("custom", pick.start, pick.end || pick.start));
    }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePicker(); });
  window.addEventListener("resize", placePicker);
  window.addEventListener("scroll", placePicker, true);

  // ---------- Range data from Invenno ----------
  let rangeSeq = 0;
  async function loadRange() {
    const seq = ++rangeSeq;
    D.rangeLoading = true;
    document.querySelectorAll(".range-scope").forEach((el) => el.classList.add("is-loading"));
    document.querySelectorAll("[data-drp] span").forEach((s) => (s.textContent = D.range.label));
    let data;
    try { data = await (await fetch(`/api/fba/range?from=${D.range.from}&to=${D.range.to}`)).json(); }
    catch { data = { error: "Couldn't reach the dashboard server." }; }
    if (seq !== rangeSeq) return; // a newer range was picked meanwhile
    D.rangeLoading = false;
    D.rangeData = data.error ? null : data;
    D.rangeError = data.error || null;
    const h = location.hash.slice(1) || "overview";
    if (h === "fba" || h === "overview") render();
  }

  // ---------- Claims & Leaks (ReclaimHQ) ----------
  const urgency = (d) => d === null || d === undefined ? "blue" : d <= 7 ? "red" : d <= 14 ? "amber" : "blue";
  const daysChip = (d) => d === null || d === undefined ? "" : `<span class="chip tint-${urgency(d)}">${d <= 0 ? "Overdue" : d + "d left"}</span>`;

  // One prioritised to-do list from everything ReclaimHQ knows
  function actionItems() {
    const r = D.reclaim;
    if (!r || !r.configured || !r.dashboard) return [];
    const items = [];
    (r.dashboard.radar || []).forEach((x) => items.push({ kind: "Deadline", verb: "Assess & file claim", title: x.title, sub: x.asin, value: x.value, days: x.days, url: "/orders?expiring=14" }));
    const radarDays = new Set((r.dashboard.radar || []).map((x) => x.days));
    (r.expiring || []).filter((o) => !o.cases && !radarDays.has(o.deadlineDays)).forEach((o) => items.push({ kind: "Removal order", verb: "Check order before window closes", title: `Removal order ${o.orderId}`, sub: `${o.detail} · ${o.status}`, value: null, days: o.deadlineDays, url: o.link || "/orders?expiring=14" }));
    (r.claims || []).filter((c) => /action|required|respond|info/i.test(c.status || "")).forEach((c) => items.push({ kind: "Claim", verb: "Reply to Amazon", title: c.product, sub: `Case ${c.caseId || "—"} · ${c.status}`, value: _gbpNum(c.value), days: c.expiryDays, url: "/claims" }));
    (r.leaks || []).filter((l) => /detected|verified/i.test(l.status || "") && l.expiresDays !== null && l.expiresDays <= 30).forEach((l) => items.push({ kind: "Leak", verb: "Open underpayment case", title: l.product, sub: `Reimb. ${l.reimbursementId} · paid ${gbp(l.reimbursed)} vs COG ${gbp(l.cog)}`, value: l.shortfall, days: l.expiresDays, url: "/leak-detector" }));
    return items.sort((a, b) => (a.days ?? 999) - (b.days ?? 999));
  }
  function _gbpNum(s) { const m = /£\s?([\d,]+(?:\.\d+)?)/.exec(s || ""); return m ? parseFloat(m[1].replace(/,/g, "")) : null; }

  function actionList(items, limit) {
    if (!items.length) return `<div class="empty">Nothing needs action right now ✓</div>`;
    return `<div class="list">${items.slice(0, limit).map((a) => `
      <a class="list-item action-item ${a.days != null && a.days <= 3 ? "urgent" : ""}" href="https://reclaimhq.uk${a.url}" target="_blank" rel="noopener">
        <span class="kpi-icon tint-${urgency(a.days)}">${icon(a.kind === "Leak" ? "pound" : a.kind === "Claim" ? "shield" : "clock")}</span>
        <div class="list-body"><div class="list-title">${esc(a.title)}</div><div class="list-meta">${esc(a.verb)} · ${esc(a.sub)}</div></div>
        <div class="list-right">${daysChip(a.days)}${a.value != null ? `<div class="cell-sub" style="margin-top:3px">${gbp(a.value)}</div>` : ""}</div>
      </a>`).join("")}</div>`;
  }

  function reclaimBanner() {
    const r = D.reclaim || {};
    if (r.loading || r.configured === null) return `<div class="banner ok">${icon("refresh")}Fetching your claims from ReclaimHQ… the first load takes about 30 seconds.</div>`;
    if (!r.configured) return `<div class="banner">${icon("alert")}<span>Connect ReclaimHQ once: double-click <code>connect-reclaimhq.bat</code> in <code>Documents\\command-centre</code> and log in.</span></div>`;
    return (r.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("");
  }

  views.claims = () => {
    const r = D.reclaim || {}, d = r.dashboard || {}, cc = r.claimCounts || {}, ls = r.leakStats || {};
    const items = actionItems();
    const statusTint = (s) => /won/i.test(s) ? "green" : /lost|denied/i.test(s) ? "red" : /under|action|required/i.test(s) ? "amber" : "blue";
    return `
      ${pageHead("Claims & Leaks", r.configured ? `Live from ReclaimHQ · updated ${r.updated}${d.lastSynced ? ` · Amazon data synced ${d.lastSynced}` : ""}` : "Removal orders, claims, deadlines and reimbursement leaks.",
        `<button class="btn" id="reclaimRefresh">${icon("refresh")}Refresh</button><a class="btn" href="https://reclaimhq.uk/dashboard" target="_blank" rel="noopener">${icon("ext")}Open ReclaimHQ</a>`)}
      ${reclaimBanner()}
      ${r.configured ? `
      <div class="grid">
        <div class="span-3">${kpi({ label: "At risk · 14 days", value: gbp(d.atRisk14), foot: d.atRiskNote || "", ic: "alert", tint: "red" })}</div>
        <div class="span-3">${kpi({ label: "Leak shortfall", value: gbp(d.leakShortfall), foot: d.expiredWinnable ? `+${gbp(d.expiredWinnable)} expired, still winnable` : `${ls.total ?? 0} underpaid reimbursements`, ic: "pound", tint: "amber" })}</div>
        <div class="span-3">${kpi({ label: "Recovered · 30 days", value: gbp(d.recovered30), foot: "verified by Amazon", ic: "trend", tint: "green" })}</div>
        <div class="span-3">${kpi({ label: "Recovered · all time", value: gbp(d.recoveredAllTime), foot: `${d.openOrders ?? "—"} open removal orders`, ic: "shield", tint: "accent" })}</div>

        <div class="card span-5">
          <div class="card-head"><div><div class="card-title">Action plan</div><div class="card-sub">Everything with a deadline, most urgent first</div></div><span class="chip tint-${items.length ? "red" : "green"}">${items.length} to do</span></div>
          ${actionList(items, 12)}
        </div>

        <div class="card flush span-7">
          <div class="card-head"><div><div class="card-title">Claims</div><div class="card-sub">${cc.all ?? 0} total · ${cc.recovered != null ? gbp(cc.recovered) + " recovered" : ""}</div></div>
            <div class="row-flex" style="gap:6px;flex-wrap:wrap">
              <span class="chip tint-amber">${cc.actionRequired ?? 0} action</span><span class="chip tint-blue">${cc.active ?? 0} active</span>
              <span class="chip tint-green">${cc.won ?? 0} won</span><span class="chip tint-red">${cc.lost ?? 0} lost</span>
            </div></div>
          <div class="table-wrap" style="margin-top:8px"><table>
            <thead><tr><th>Product</th><th>Status</th><th>Case</th><th class="num">Expiry</th><th class="num">Value</th></tr></thead>
            <tbody>${(r.claims || []).length ? r.claims.map((c) => `
              <tr>
                <td><div class="row-flex">${c.image ? `<img class="thumb" src="${esc(c.image)}" alt="" style="object-fit:contain;background:#fff;padding:2px">` : `<span class="thumb tint-accent">${icon("shield")}</span>`}
                  <div><div class="cell-main" style="max-width:300px;overflow:hidden;text-overflow:ellipsis">${esc(c.product)}</div><div class="cell-sub">${esc(c.order || "")}</div></div></div></td>
                <td><span class="chip tint-${statusTint(c.status)}">${esc(c.status || "—")}</span></td>
                <td class="cell-sub mono">${esc(c.caseId || "—")}</td>
                <td class="num">${c.expiryDays != null ? daysChip(c.expiryDays) : '<span class="cell-sub">—</span>'}</td>
                <td class="num">${esc(c.value || "—")}</td>
              </tr>`).join("") : `<tr><td colspan="5" class="cell-sub" style="text-align:center;padding:30px">No claims</td></tr>`}</tbody></table></div>
        </div>

        <div class="card flush span-12">
          <div class="card-head"><div><div class="card-title">Leak detector · reimbursements under cost</div><div class="card-sub">${ls.total ?? 0} leaks · ${gbp(ls.shortfall)} shortfall · ${ls.openCases ?? 0} open cases${ls.recovered ? ` · ${gbp(ls.recovered)} recovered` : ""}</div></div>
            <a class="link" href="https://reclaimhq.uk/leak-detector" target="_blank" rel="noopener">Open cases in ReclaimHQ</a></div>
          <div class="table-wrap" style="margin-top:8px"><table>
            <thead><tr><th>Product</th><th>Reimbursement</th><th class="num">Paid</th><th class="num">COG ex VAT</th><th class="num">Shortfall</th><th class="num">Expires</th><th>Status</th></tr></thead>
            <tbody>${(r.leaks || []).length ? r.leaks.map((l) => `
              <tr>
                <td><div class="cell-main" style="max-width:380px;overflow:hidden;text-overflow:ellipsis">${esc(l.product)}</div></td>
                <td><div class="mono cell-sub">${esc(l.reimbursementId)}</div><div class="cell-sub">${esc(l.date || "")}</div></td>
                <td class="num">${gbp(l.reimbursed)}</td><td class="num">${gbp(l.cog)}</td>
                <td class="num down" style="font-weight:600">${gbp(l.shortfall)}</td>
                <td class="num">${daysChip(l.expiresDays)}</td>
                <td><span class="chip tint-${statusTint(l.status)}">${esc(l.status || "—")}</span></td>
              </tr>`).join("") : `<tr><td colspan="7" class="cell-sub" style="text-align:center;padding:30px">No leaks detected</td></tr>`}</tbody></table></div>
        </div>

        <div class="card flush span-12">
          <div class="card-head"><div><div class="card-title">Removal orders · filing deadline within 14 days</div><div class="card-sub">${r.ordersStats?.totalOrders ?? "—"} orders · ${r.ordersStats?.totalItems ?? "—"} items tracked · ${gbp(r.ordersStats?.atRisk)} at risk</div></div></div>
          <div class="table-wrap" style="margin-top:8px"><table>
            <thead><tr><th>Removal order</th><th>Status</th><th class="num">Cases</th><th>Created</th><th class="num">Deadline</th></tr></thead>
            <tbody>${(r.expiring || []).length ? r.expiring.map((o) => `
              <tr>
                <td><a class="cell-main mono" href="https://reclaimhq.uk${esc(o.link || "/orders")}" target="_blank" rel="noopener">${esc(o.orderId)}</a><div class="cell-sub">${esc(o.detail)}</div></td>
                <td><span class="chip tint-${o.cases ? "blue" : "amber"}">${esc(o.status || "—")}</span></td>
                <td class="num">${o.cases ?? 0}</td><td class="cell-sub">${esc(o.created || "")}</td>
                <td class="num">${daysChip(o.deadlineDays)}</td>
              </tr>`).join("") : `<tr><td colspan="5" class="cell-sub" style="text-align:center;padding:30px">Nothing expiring in the next 14 days</td></tr>`}</tbody></table></div>
        </div>
      </div>` : ""}`;
  };

  async function loadReclaim(force) {
    let d;
    try { d = await (await fetch("/api/reclaim" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    D.reclaim = d;
    const n = actionItems().length, urgent = actionItems().filter((a) => a.days !== null && a.days <= 7).length;
    const navCount = document.querySelector('.nav-item[href="#claims"] .count');
    if (navCount) { navCount.textContent = n; navCount.style.display = n ? "" : "none"; navCount.classList.toggle("hot", urgent > 0); }
    const badge = document.querySelector(".has-badge .badge");
    if (badge && d.configured) { badge.textContent = n; badge.style.display = n ? "" : "none"; }
    const h = location.hash.slice(1) || "overview";
    buildTicker();
    if (h === "claims" || h === "overview") render();
    if (d.loading) setTimeout(loadReclaim, 6000);
  }
  D.reclaim = { loading: true };
  loadReclaim();
  setInterval(loadReclaim, 5 * 60 * 1000);
  document.addEventListener("click", (e) => {
    if (e.target.closest("#reclaimRefresh")) { D.reclaim = { ...D.reclaim, loading: true }; render(); fetch("/api/reclaim?refresh=1").then(() => setTimeout(loadReclaim, 30000)); }
  });

  views.jobs = () => {
    const J = D.jobs, live = D.jobsLive, c = J.counts || {};
    const site = J.site || "https://job-dashboard.example.com/";
    const stageTint = (s) => /offer/i.test(s) ? "green" : /interview|centre|screening/i.test(s) ? "accent" : /assessment|questions/i.test(s) ? "amber" : "blue";
    const ago = (iso) => {
      if (!iso) return "";
      const days = Math.round((new Date(new Date().toDateString()) - new Date(iso)) / 864e5);
      return days <= 0 ? "Today" : days === 1 ? "Yesterday" : days + "d ago";
    };
    const banner = J.loading ? `<div class="banner ok">${icon("refresh")}Loading your job hunt…</div>`
      : (J.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("");
    if (!live) return `
      ${pageHead("Job Hunt", "Matches from the job scraper and your application tracker.", `<a class="btn" href="${site}" target="_blank" rel="noopener">${icon("ext")}Job dashboard</a>`)}
      ${banner}`;
    return `
    ${pageHead("Job Hunt", `Live from Airtable + Google Sheets · updated ${J.updated} · ${c.scraped.toLocaleString("en-GB")} jobs scraped`,
      `<button class="btn" id="jobsRefresh">${icon("refresh")}Refresh</button>
       <a class="btn" href="https://airtable.com/" target="_blank" rel="noopener">${icon("ext")}Airtable</a>
       <a class="btn" href="https://sheets.google.com/" target="_blank" rel="noopener">${icon("ext")}Tracker sheet</a>
       <a class="btn primary" href="${site}" target="_blank" rel="noopener">${icon("ext")}Job dashboard</a>`)}
    ${banner}
    <div class="grid">
      <div class="span-3">${kpi({ label: "Top matches · this week", value: c.goodWeek, foot: `${c.goodToday} today · rated 9–10`, ic: "briefcase", tint: "green" })}</div>
      <div class="span-3">${kpi({ label: "Applied · this week", value: c.appliedWeek, foot: `${c.applications} applications all time`, ic: "trend", tint: "accent" })}</div>
      <div class="span-3">${kpi({ label: "In process", value: J.inProcess.length, foot: "assessments, screens & interviews", ic: "clock", tint: "amber" })}</div>
      <div class="span-3">${kpi({ label: "Awaiting reply", value: J.pipeline.find((p) => p.label === "Awaiting reply")?.n ?? 0, foot: `${J.pipeline.find((p) => p.label === "Rejected")?.n ?? 0} rejected so far`, ic: "note", tint: "blue" })}</div>

      <div class="card span-12"><div class="card-head"><div class="card-title">Pipeline</div><span class="card-sub">Matches from Airtable · applications from the tracker sheet</span></div>${pipeline()}</div>

      <div class="card span-5">
        <div class="card-head"><div><div class="card-title">In process</div><div class="card-sub">Tracker sheet · next steps you've reached</div></div><span class="chip tint-amber">${J.inProcess.length}</span></div>
        ${J.inProcess.length ? `<div class="list">${J.inProcess.map((f) => `
          <div class="list-item" style="align-items:flex-start">
            <span class="thumb tint-${stageTint(f.status)}">${initials(f.company)}</span>
            <div class="list-body">
              <div class="row-flex" style="justify-content:space-between;gap:8px"><div class="list-title">${esc(f.company)}</div><span class="chip tint-${stageTint(f.status)}">${esc(f.status)}</span></div>
              <div class="list-meta">${esc(f.role)}</div>
              ${f.notes ? `<div class="list-meta job-note">${esc(f.notes)}</div>` : ""}
            </div>
          </div>`).join("")}</div>` : `<div class="empty">Nothing in process yet</div>`}
      </div>

      <div class="card flush span-7">
        <div class="card-head"><div><div class="card-title">Newest top matches</div><div class="card-sub">Airtable · rated 9–10 against your CV · not yet applied</div></div>
          <a class="link" href="${site}" target="_blank" rel="noopener">Apply from dashboard</a></div>
        <div class="table-wrap" style="margin-top:8px"><table>
          <thead><tr><th>Role</th><th>Location</th><th class="num">Rating</th><th class="num">Found</th></tr></thead>
          <tbody>${J.matches.map((j) => `
            <tr class="job-row" data-href="${esc(j.url || "")}">
              <td><div class="row-flex"><span class="thumb tint-accent">${initials(j.company || "?")}</span>
                <div><div class="cell-main" style="max-width:330px;overflow:hidden;text-overflow:ellipsis">${esc(j.title)}</div><div class="cell-sub">${esc(j.company)} · ${esc(j.source || "")}</div></div></div></td>
              <td class="cell-sub" style="max-width:160px;overflow:hidden;text-overflow:ellipsis">${esc(j.location)}</td>
              <td class="num"><span class="chip tint-${j.rating >= 10 ? "green" : "blue"}">${j.rating}/10</span></td>
              <td class="num cell-sub">${ago(j.found)}</td>
            </tr>`).join("")}</tbody></table></div>
      </div>

      <div class="card span-7">
        <div class="card-head"><div><div class="card-title">Applications per day</div><div class="card-sub">Last 30 days · ${J.applied30.reduce((a, b) => a + b, 0)} total</div></div></div>
        ${barChart(J.applied30, J.appliedLabels, { h: 190, color: "--accent", unit: "applications", every: 5 })}
      </div>

      <div class="card span-5">
        <div class="card-head"><div class="card-title">Latest updates</div><a class="link" href="${site}updates.html" target="_blank" rel="noopener">Timeline</a></div>
        <div class="list">${J.recent.slice(0, 8).map((u) => `
          <div class="list-item">
            <span class="dot ${/denied|reject/i.test(u.change) ? "err" : /applied|waiting/i.test(u.change) ? "idle" : "ok"}"></span>
            <div class="list-body"><div class="list-title">${esc(u.company)} · ${esc(u.change)}</div><div class="list-meta">${esc(u.role)}</div></div>
            <div class="list-right cell-sub">${ago(u.date)}</div>
          </div>`).join("")}</div>
      </div>
    </div>`;
  };

  async function loadJobs(force) {
    let d;
    try { d = await (await fetch("/api/jobs" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    if (d.configured && d.matches) {
      D.jobs = { ...d, appliedThisWeek: d.counts.appliedWeek, followUps: d.inProcess };
      D.jobsLive = true;
      const nav = document.querySelector('.nav-item[href="#jobs"] .count');
      if (nav) nav.textContent = d.counts.goodToday || d.inProcess.length;
    } else {
      D.jobs = { ...D.jobs, loading: !!d.loading, errors: d.errors };
    }
    const h = location.hash.slice(1) || "overview";
    if (h === "jobs" || h === "overview") render();
    if (d.loading) setTimeout(loadJobs, 4000);
  }
  loadJobs();
  setInterval(loadJobs, 5 * 60 * 1000);
  document.addEventListener("click", (e) => {
    if (e.target.closest("#jobsRefresh")) { fetch("/api/jobs?refresh=1").then(() => setTimeout(loadJobs, 8000)); }
    const row = e.target.closest(".job-row");
    if (row && row.dataset.href) window.open(row.dataset.href, "_blank", "noopener");
  });

  views.isa = () => {
    const s = D.isa;
    if (!D.isaLive) return `
      ${pageHead("Stocks & Shares ISA", "Vanguard holdings at live prices.", "")}
      ${s.errors ? s.errors.map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("") : `<div class="banner ok">${icon("refresh")}Fetching live prices…</div>`}`;
    const PAL = ["--accent", "--blue", "--green", "--amber", "--red", "#c084fc", "#94a3b8"];
    const colorOf = (i) => PAL[i % PAL.length];
    const varOr = (c) => c.startsWith("--") ? `var(${c})` : c;
    const signed = (n, money = true) => `${n >= 0 ? "+" : "−"}${money ? gbp(Math.abs(n)) : Math.abs(n).toFixed(2) + "%"}`;
    const labels = s.historyDates.map((d) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" }));
    const firstVal = s.history[0], periodChange = s.value - firstVal;
    const alloc = s.holdings.map((h, i) => ({ label: h.ticker, weight: h.weight, color: colorOf(i) }));
    if (s.cash) alloc.push({ label: "Cash", weight: +(s.cash / s.value * 100).toFixed(2), color: "#475569" });
    return `
      ${pageHead("Stocks & Shares ISA", `${esc(s.account)} · live prices · updated ${s.updated} · display only, not financial advice`,
        `<button class="btn" id="isaEdit">${icon("note")}Edit holdings</button>
         <button class="btn" id="isaRefresh">${icon("refresh")}Refresh</button>
         <a class="btn" href="https://secure.vanguardinvestor.co.uk/" target="_blank" rel="noopener">${icon("ext")}Vanguard</a>`)}
      ${(s.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("")}
      <div class="grid">
        <div class="span-4">${kpi({ label: "Portfolio value", value: gbp(s.value), delta: s.dayPct, foot: `${signed(s.day)} today`, ic: "chart", tint: "blue" })}</div>
        <div class="span-4">${kpi({ label: "Total return", value: s.return != null ? signed(s.return) : "—", foot: s.netContributions ? `value minus ${gbp(s.netContributions, 0)} paid in` : "add net contributions", ic: "trend", tint: "green" })}</div>
        <div class="span-3 isa-hide">${kpi({ label: "6-month change", value: signed(periodChange), delta: firstVal ? (periodChange / firstVal) * 100 : 0, foot: "current holdings, at past prices", ic: "clock", tint: "accent" })}</div>
        <div class="span-4">${kpi({ label: "Fees · weighted OCF", value: s.ocf.toFixed(2) + "%", foot: `≈ ${gbp(s.annualFees)} a year · ${gbp(s.cash)} cash`, ic: "pound", tint: "amber" })}</div>
        <div class="card span-12 isa-strip"><span>6-month change <b class="${s.history.length && s.value - s.history[0] >= 0 ? "up" : "down"}">${signed(s.value - s.history[0])}</b></span><span class="cell-sub">Total return = account value minus money paid in, matching Vanguard's account card.</span></div>

        <div class="card span-8">
          <div class="card-head"><div><div class="card-title">Portfolio value</div><div class="card-sub">Last 6 months · today's units at each day's closing price</div></div></div>
          ${areaChart(s.history, { labels, fmt: (v) => "£" + Math.round(v).toLocaleString("en-GB"), h: 250, color: "--blue", fitMin: true })}
        </div>

        <div class="card span-4">
          <div class="card-head"><div class="card-title">Allocation</div></div>
          <div class="donut-wrap" style="justify-content:center">
            ${donut(alloc)}
            <div class="donut-legend">${alloc.map((a) => `<div class="row-flex"><span><i style="background:${varOr(a.color)}"></i>${a.label}</span><span class="cell-sub">${a.weight}%</span></div>`).join("")}</div>
          </div>
        </div>

        <div class="card flush span-12">
          <div class="card-head"><div><div class="card-title">Holdings</div><div class="card-sub">Units as of ${s.holdingsAsOf} · ETFs priced live, index funds at their daily price</div></div></div>
          <div class="table-wrap" style="margin-top:8px"><table>
            <thead><tr><th>Holding</th><th class="num">Units</th><th class="num">Avg cost</th><th class="num">Price</th><th class="num">Value</th><th class="num">Gain</th><th class="num">Today</th><th class="num">Weight</th></tr></thead>
            <tbody>${s.holdings.map((h, i) => `
              <tr>
                <td><div class="row-flex"><span class="thumb" style="background:color-mix(in srgb, ${varOr(colorOf(i))} 16%, transparent);color:${varOr(colorOf(i))}">${h.ticker.slice(0, 2)}</span>
                  <div><div class="cell-main">${h.ticker}</div><div class="cell-sub">${esc(h.name)}</div></div></div></td>
                <td class="num">${h.units.toLocaleString("en-GB", { maximumFractionDigits: 4 })}</td>
                <td class="num cell-sub">${gbp(h.avgCost)}</td>
                <td class="num">${gbp(h.price)}<div class="cell-sub">${h.priced === "live" ? '<span class="up">● live</span>' : esc(h.priced)}</div></td>
                <td class="num" style="font-weight:600">${gbp(h.value)}</td>
                <td class="num ${h.gain >= 0 ? "up" : "down"}">${signed(h.gain)}<div class="cell-sub">${signed(h.gainPct, false)}</div></td>
                <td class="num ${h.day >= 0 ? "up" : "down"}">${signed(h.dayPct, false)}</td>
                <td class="num cell-sub">${h.weight}%</td>
              </tr>`).join("")}
              <tr><td><div class="row-flex"><span class="thumb" style="background:var(--panel-2)">£</span><div class="cell-main">Cash</div></div></td>
                <td colspan="3"></td><td class="num" style="font-weight:600">${gbp(s.cash)}</td><td colspan="3"></td></tr>
            </tbody></table></div>
        </div>
      </div>`;
  };

  // ---------- Holdings editor ----------
  function openIsaEditor() {
    const s = D.isa;
    const wrap = document.createElement("div");
    wrap.className = "palette-bg open";
    wrap.innerHTML = `
      <div class="palette" style="width:min(640px,calc(100vw - 32px))">
        <div style="padding:18px 20px;border-bottom:1px solid var(--border-soft)"><div class="card-title">Edit holdings</div>
          <div class="card-sub">After you buy or sell, copy <b>My units</b> and <b>Total cost</b> from Vanguard → Investments → Detailed view.</div></div>
        <div style="padding:8px 20px;max-height:60vh;overflow:auto"><table>
          <thead><tr><th style="padding-left:0">Holding</th><th class="num">Units</th><th class="num">Total cost (£)</th></tr></thead>
          <tbody>${s.holdings.map((h) => `
            <tr><td style="padding-left:0"><div class="cell-main">${h.ticker}</div><div class="cell-sub">${esc(h.name)}</div></td>
              <td class="num"><input class="isa-in" data-t="${h.ticker}" data-f="units" value="${h.units}" inputmode="decimal"></td>
              <td class="num"><input class="isa-in" data-t="${h.ticker}" data-f="totalCost" value="${h.cost}" inputmode="decimal"></td></tr>`).join("")}
            <tr><td style="padding-left:0"><div class="cell-main">Cash</div></td><td></td>
              <td class="num"><input class="isa-in" data-f="cash" value="${s.cash}" inputmode="decimal"></td></tr>
            <tr><td style="padding-left:0"><div class="cell-main">Net paid in</div><div class="cell-sub">Add each new deposit (minus withdrawals)</div></td><td></td>
              <td class="num"><input class="isa-in" data-f="netContributions" value="${s.netContributions ?? ""}" inputmode="decimal"></td></tr>
          </tbody></table></div>
        <div class="palette-foot" style="justify-content:flex-end;gap:8px"><span class="isa-msg" style="margin-right:auto"></span>
          <button class="btn" data-isa-cancel>Cancel</button><button class="btn primary" data-isa-save>Save</button></div>
      </div>`;
    document.body.appendChild(wrap);
    const close = () => wrap.remove();
    wrap.addEventListener("click", async (e) => {
      if (e.target === wrap || e.target.closest("[data-isa-cancel]")) return close();
      if (!e.target.closest("[data-isa-save]")) return;
      const holdings = {}, body = { holdings: [] };
      let bad = false;
      wrap.querySelectorAll(".isa-in").forEach((i) => {
        const v = parseFloat(i.value);
        if (!isFinite(v) || v < 0) { bad = true; i.style.borderColor = "var(--red)"; }
        if (i.dataset.f === "cash") body.cash = v;
        else if (i.dataset.f === "netContributions") body.netContributions = v;
        else (holdings[i.dataset.t] ||= { ticker: i.dataset.t })[i.dataset.f] = v;
      });
      if (bad) { wrap.querySelector(".isa-msg").textContent = "Check the highlighted numbers"; return; }
      body.holdings = Object.values(holdings);
      wrap.querySelector(".isa-msg").textContent = "Saving & repricing…";
      const r = await (await fetch("/api/isa/holdings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).json();
      if (!r.ok) { wrap.querySelector(".isa-msg").textContent = r.error || "Save failed"; return; }
      setIsa(r.isa); close(); render();
    });
  }

  function setIsa(d) {
    D.isa = { ...d, dayChangePct: d.dayPct, dayChange: d.day };
    D.isaLive = true;
  }
  async function loadIsa(force) {
    let d;
    try { d = await (await fetch("/api/isa" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    if (d.configured && d.holdings) { setIsa(d); buildTicker(); }
    else D.isa = { ...D.isa, errors: d.errors };
    const h = location.hash.slice(1) || "overview";
    if (h === "isa" || h === "overview") render();
    if (d.loading) setTimeout(loadIsa, 4000);
  }
  loadIsa();
  setInterval(loadIsa, 5 * 60 * 1000);
  document.addEventListener("click", (e) => {
    if (e.target.closest("#isaEdit")) openIsaEditor();
    if (e.target.closest("#isaRefresh")) fetch("/api/isa?refresh=1").then(() => setTimeout(loadIsa, 6000));
  });

  // ---------- Deal monitors (oa-bot) ----------
  const relTime = (iso) => {
    if (!iso) return "—";
    const m = Math.round((Date.now() - new Date(iso)) / 60000);
    if (m < 1) return "just now";
    if (m < 60) return m + "m ago";
    if (m < 60 * 24) return Math.round(m / 60) + "h ago";
    const d = Math.round(m / 1440);
    return d === 1 ? "yesterday" : d + "d ago";
  };
  const isProfitLead = (l) => l.source !== "HUKD";
  let dealFilter = "Profit leads";

  views.deals = () => {
    const DL = D.deals, live = D.dealsLive;
    if (!live) return `${pageHead("Deal Monitors", "Status and leads from your oa-bot monitors.", "")}
      <div class="banner ok">${icon("refresh")}Reading your monitors…</div>`;
    const t = DL.totals;
    const open = DL.leads.filter((l) => !l.status);
    const counts = { bought: 0, declined: 0, oos: 0 };
    DL.leads.forEach((l) => { if (l.status) counts[l.status]++; });
    const statusOf = { "✅ Bought": "bought", "✕ Declined": "declined", "⌀ Out of stock": "oos" };
    const filters = ["Profit leads", ...DL.monitors.map((m) => m.store), ...Object.keys(statusOf)];
    const shown = statusOf[dealFilter]
      ? DL.leads.filter((l) => l.status === statusOf[dealFilter]).sort((a, b) => (b.statusAt || "").localeCompare(a.statusAt || ""))
      : (dealFilter === "Profit leads" ? open.filter(isProfitLead) : open.filter((l) => l.source === dealFilter)).sort((a, b) => (b.topPick ? 1 : 0) - (a.topPick ? 1 : 0));
    const profitPerDay = DL.days.map((_, i) => Object.entries(DL.perDay).filter(([s]) => s !== "HUKD").reduce((a, [, v]) => a + v[i], 0));
    return `
    ${pageHead("Deal Monitors", `Live from oa-bot logs · ${t.running}/${t.count} running · updated ${DL.updated}`,
      `<button class="btn" id="dealsRefresh">${icon("refresh")}Refresh</button>`)}
    ${(DL.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("")}
    ${DL.monitors.filter((m) => !m.running).map((m) => `<div class="banner">${icon("alert")}<span><b>${esc(m.name)}</b> isn't running${m.lastActivity ? ` — last activity ${relTime(m.lastActivity)}` : ""}.</span>
        ${m.canStart ? `<button class="btn primary" style="margin-left:auto;height:30px" data-start="${m.id}">${icon("play")}Start it</button>` : ""}</div>`).join("")}
    <div class="grid">
      ${DL.monitors.map((m) => `
        <div class="card monitor span-6">
          <div class="monitor-top">
            <span class="kpi-icon tint-${{ argos: "red", tkmaxx: "accent", currys: "blue", hukd: "amber", dbh: "green", discord: "blue" }[m.id] || "accent"}">${icon("bolt")}</span>
            <div class="list-body"><div class="card-title">${esc(m.name)}</div><div class="card-sub">${esc(m.desc)}</div></div>
            ${statusChip(m.status)}
          </div>
          <div class="monitor-stats">
            <div><b>${m.leadsToday}</b><span>${m.id === "hukd" ? "Posts today" : "Leads today"}</span></div>
            <div><b>${m.leadsWeek}</b><span>Last 7 days</span></div>
            <div><b>${m.medianRoi != null ? m.medianRoi + "%" : m.bestProfit != null ? gbp(m.bestProfit, 0) : "—"}</b><span>${m.medianRoi != null ? "Median ROI" : "Best profit"}</span></div>
          </div>
          <div class="card-sub monitor-last" title="${esc(m.lastEvent || "")}">Last activity ${relTime(m.lastActivity)}${m.lastEvent ? " · " + esc(m.lastEvent) : ""}${m.warnings24h ? ` · <span class="down">${m.warnings24h} warnings (24h)</span>` : ""}</div>
        </div>`).join("")}

      <div class="card flush span-12">
        <div class="card-head"><div><div class="card-title">Leads</div><div class="card-sub">${statusOf[dealFilter] ? "Leads you marked " + esc(dealFilter.slice(2)) : dealFilter === "Profit leads" ? "Open profit-checked leads (DBH, Discord) · last 14 days" : esc(dealFilter) + " · open leads, newest first"} · ${shown.length}</div></div>
          <div class="seg deal-filter">${filters.map((f) => `<button class="${f === dealFilter ? "on" : ""}" data-deal-filter="${esc(f)}">${esc(f)}${statusOf[f] ? " · " + counts[statusOf[f]] : ""}</button>`).join("")}</div></div>
        <div style="margin-top:8px">${shown.length ? leadsTable(shown, 80, { actions: true }) : `<div class="empty">${statusOf[dealFilter] ? "Nothing here yet" : "No leads here yet"}</div>`}</div>
      </div>
      <div class="card span-8">
        <div class="card-head"><div><div class="card-title">Profit leads per day</div><div class="card-sub">Last 7 days · excludes HUKD posts</div></div></div>
        ${barChart(profitPerDay, DL.days, { h: 180, color: "--amber", unit: "leads" })}
      </div>
      <div class="card span-4">
        <div class="card-head"><div class="card-title">This week by source</div></div>
        <div class="list">${Object.entries(DL.perDay).map(([s, v]) => `
          <div class="list-item"><span class="chip tint-${sourceTint[s] || "blue"}">${esc(s)}</span><div class="list-body"></div><div class="list-right mono cell-sub">${v.reduce((a, b) => a + b, 0)} this week</div></div>`).join("")}</div>
      </div>
    </div>`;
  };

  async function loadDeals(force) {
    let d;
    try { d = await (await fetch("/api/monitors" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    if (d.configured && d.monitors) {
      const profitToday = d.leads.filter((l) => isProfitLead(l) && new Date(l.time).toDateString() === new Date().toDateString()).length;
      const days = d.days.map((_, i) => Object.entries(d.perDay).filter(([s]) => s !== "HUKD").reduce((a, [, v]) => a + v[i], 0));
      D.deals = { ...d, leads7: days, profitToday };
      D.dealsLive = true;
      const nav = document.querySelector('.nav-item[href="#deals"] .count');
      if (nav) { nav.textContent = profitToday || d.monitors.filter((m) => !m.running).length || ""; nav.style.display = nav.textContent ? "" : "none"; nav.classList.toggle("hot", d.monitors.some((m) => !m.running)); }
      // the Agents page shows the real monitor services
      const others = D.agents.filter((a) => a.kind !== "Local service" && a.name !== "OA Bot");
      D.agents = d.monitors.map((m) => ({ name: m.name, kind: "Local service", schedule: m.desc, status: m.status, last: relTime(m.lastActivity), id: m.id, canStart: m.canStart })).concat(others);
      buildTicker();
    }
    const h = location.hash.slice(1) || "overview";
    if (["deals", "overview", "agents"].includes(h)) render();
    if (d.loading) setTimeout(loadDeals, 4000);
  }
  loadDeals();
  setInterval(loadDeals, 2 * 60 * 1000);
  document.addEventListener("click", async (e) => {
    const f = e.target.closest("[data-deal-filter]");
    if (f) { dealFilter = f.dataset.dealFilter; render(); }
    if (e.target.closest("#dealsRefresh")) { await fetch("/api/monitors?refresh=1"); setTimeout(loadDeals, 3000); }
    const st = e.target.closest("[data-start]");
    if (st) {
      st.disabled = true; st.textContent = "Starting…";
      const r = await (await fetch("/api/monitors/start?id=" + st.dataset.start, { method: "POST" })).json();
      st.textContent = r.ok ? "Started ✓" : (r.error || "Couldn't start");
      setTimeout(loadDeals, 4000);
    }
    const sb = e.target.closest("[data-lead-status]");
    if (sb) {
      const key = sb.dataset.key, status = sb.dataset.leadStatus;
      const lead = D.deals.leads.find((l) => l.key === key);
      const snapshot = lead ? { ...lead, status: undefined, statusAt: undefined } : null;
      if (lead) { lead.status = status === "active" ? undefined : status; lead.statusAt = new Date().toISOString(); render(); }
      await fetch("/api/leads/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key, status, lead: snapshot }) });
      setTimeout(loadDeals, 1500);
    }
  });

  views.calendar = () => {
    const C = D.calStatus || {};
    const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d; });
    const banner = C.loading ? `<div class="banner ok">${icon("refresh")}Loading your calendar…</div>`
      : C.configured === false ? `<div class="banner">${icon("alert")}<span>Showing <b>sample events</b>. Paste your Google Calendar's <b>secret iCal address</b> into <code>Documents\\command-centre\\.env</code> (line <code>CALENDAR_ICS_1</code>) — the dashboard picks it up within 10 minutes.</span></div>`
      : (C.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("");
    const later = D.calendar.filter((e) => e.d >= 7 && e.d <= 14);
    const ev = (e) => `
      <div class="event" title="${esc([e.title, e.location, e.calendar].filter(Boolean).join(" · "))}" style="border-color:var(${kindColor[e.kind]});background:color-mix(in srgb, var(${kindColor[e.kind]}) 10%, transparent)">
        <div class="t">${e.t}${e.end ? "–" + e.end : ""}</div>${esc(e.title)}${e.location ? `<div class="t">${esc(e.location)}</div>` : ""}</div>`;
    return `
      ${pageHead("Calendar", D.calLive ? `Google Calendar · ${esc((C.calendars || []).join(", "))} · updated ${C.updated}` : "The next 7 days across business, job hunt and personal.",
        `<div class="chart-legend" style="align-self:center"><span><i style="background:var(--accent)"></i>Business</span><span><i style="background:var(--green)"></i>Job hunt</span><span><i style="background:var(--amber)"></i>Personal</span></div>
         ${D.calLive ? `<button class="btn" id="calRefresh">${icon("refresh")}Refresh</button><a class="btn" href="https://calendar.google.com/" target="_blank" rel="noopener">${icon("ext")}Google Calendar</a>` : ""}`)}
      ${banner}
      <div class="card"><div class="week">${days.map((d, i) => `
        <div class="day ${i === 0 ? "today" : ""}">
          <div class="day-h"><span>${i === 0 ? "Today" : i === 1 ? "Tomorrow" : d.toLocaleDateString("en-GB", { weekday: "short" })}</span><b>${d.getDate()}</b></div>
          ${D.calendar.filter((e) => e.d === i).map(ev).join("") || '<div class="cell-sub">Free</div>'}
        </div>`).join("")}</div></div>
      ${D.calLive ? `
      <div class="card" style="margin-top:16px">
        <div class="card-head"><div class="card-title">Week after</div><span class="card-sub">${later.length} events</span></div>
        ${later.length ? `<div class="list">${later.map((e) => {
          const day = new Date(); day.setDate(day.getDate() + e.d);
          return `<div class="list-item"><span class="agenda-time" style="width:86px">${day.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}</span>
            <span class="agenda-bar" style="background:var(${kindColor[e.kind]})"></span>
            <div class="list-body"><div class="list-title">${esc(e.title)}</div><div class="list-meta">${e.t}${e.location ? " · " + esc(e.location) : ""} · ${esc(e.calendar)}</div></div></div>`;
        }).join("")}</div>` : `<div class="empty">Nothing booked</div>`}
      </div>` : ""}`;
  };

  // ---------- Live calendar ----------
  async function loadCalendar(force) {
    let d;
    try { d = await (await fetch("/api/calendar" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    D.calStatus = d;
    if (d.configured && d.events) {
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const hm = (dt) => dt.toTimeString().slice(0, 5);
      D.calendar = d.events.map((e) => {
        const s = new Date(e.start), en = new Date(e.end);
        const day = new Date(s); day.setHours(0, 0, 0, 0);
        return { d: Math.round((day - today) / 864e5), t: e.allDay ? "All day" : hm(s), end: e.allDay ? "" : hm(en),
                 title: e.title, kind: e.kind, location: e.location, calendar: e.calendar };
      }).filter((e) => e.d >= 0);
      D.calLive = true;
    }
    const h = location.hash.slice(1) || "overview";
    if (h === "calendar" || h === "overview") render();
    if (d.loading) setTimeout(loadCalendar, 4000);
  }
  D.calStatus = { loading: true };
  loadCalendar();
  setInterval(loadCalendar, 5 * 60 * 1000);
  document.addEventListener("click", (e) => {
    if (e.target.closest("#calRefresh")) fetch("/api/calendar?refresh=1").then(() => setTimeout(loadCalendar, 4000));
  });

  // ---------- Important emails ----------
  let impFilter = "All";
  const impDoneKey = "cc-important-done";
  const impDone = () => { try { return new Set(JSON.parse(localStorage.getItem(impDoneKey) || "[]")); } catch { return new Set(); } };
  const prioTint = { 1: "red", 2: "amber", 3: "blue" };
  const prioLabel = { 1: "High", 2: "Medium", 3: "Low" };
  const catIcon = { Job: "briefcase", Money: "pound", Business: "box", Security: "shield", Life: "calendar", People: "note", Other: "alert" };

  function impItems() {
    const I = D.important || {};
    const done = impDone();   // old browser-only list, still honoured; Done now lives on the server (x.done)
    return (I.items || []).filter((x) => !x.done && !done.has(x.id));
  }

  function impCard(x) {
    const when = x.eventDate ? new Date(x.eventDate).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", ...(x.eventTimed ? { hour: "2-digit", minute: "2-digit" } : {}) }) : null;
    return `
      <div class="imp-item prio-${x.priority} ${x.unread ? "unread" : ""} ${x.priority === 1 && x.unread ? "urgent" : ""}">
        <span class="kpi-icon tint-${prioTint[x.priority]}">${icon(catIcon[x.category] || "alert")}</span>
        <div class="list-body">
          <div class="row-flex" style="gap:8px;flex-wrap:wrap">
            <span class="chip tint-${prioTint[x.priority]}">${prioLabel[x.priority]}</span>
            <span class="chip" style="background:var(--panel-2);color:var(--text-2)">${esc(x.reason)}</span>
            ${x.unread ? '<span class="chip tint-accent">Unread</span>' : ""}
            ${x.count > 1 ? `<span class="chip" style="background:var(--panel-2);color:var(--text-2)">×${x.count} emails</span>` : ""}
            <span class="cell-sub" style="margin-left:auto">${relTime(x.received)}</span>
          </div>
          <div class="imp-subject">${esc(x.subject)}</div>
          <div class="list-meta">${esc(x.from)} · to ${esc(x.to && x.to !== x.account ? x.to : x.account)}</div>
          <div class="imp-snippet">${esc(x.snippet)}</div>
          <div class="row-flex imp-actions">
            <a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">${icon("ext")}${String(x.url).includes("icloud.com") ? "Open iCloud Mail" : "Open in Gmail"}</a>
            ${x.calendarUrl ? `<a class="btn primary" href="${esc(x.calendarUrl)}" target="_blank" rel="noopener">${icon("calendar")}Add to calendar · ${esc(when)}</a>` : ""}
            <button class="btn" data-imp-done="${esc(x.id)}" data-imp-group="${esc(x.groupKey || "")}" title="Hides it on all your devices, and repeats of it for 7 days">${icon("plus")}Done</button>
          </div>
        </div>
      </div>`;
  }

  views.important = () => {
    const I = D.important || {};
    if (I.loading || I.configured === null) return `${pageHead("Important", "Emails worth your attention.", "")}<div class="banner ok">${icon("refresh")}Checking your inbox…</div>`;
    if (!I.configured) return `${pageHead("Important", "Emails worth your attention.", "")}
      <div class="banner">${icon("alert")}<span>Add a Gmail <b>app password</b> (line <code>GMAIL_1=address|app-password</code>) to <code>Documents\\command-centre\\.env</code> (line <code>GMAIL_1</code>) — create one at <a class="link" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener">myaccount.google.com/apppasswords</a>.</span></div>`;
    const all = impItems();
    const cats = ["All", "High", ...[...new Set(all.map((x) => x.category))]];
    const shown = impFilter === "All" ? all : impFilter === "High" ? all.filter((x) => x.priority === 1) : all.filter((x) => x.category === impFilter);
    const hidden = (I.items || []).length - all.length;
    return `
      ${pageHead("Important", `${esc((I.accounts || []).join(", "))} · last ${I.days} days · checked ${I.updated}`,
        `<button class="btn" id="impRefresh">${icon("refresh")}Refresh</button>${hidden ? `<button class="btn" id="impRestore">Show ${hidden} done</button>` : ""}`)}
      ${(I.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("")}
      <div class="card" style="margin-bottom:16px">
        <div class="card-head"><div><div class="card-title">📦 Delivery codes</div><div class="card-sub">Amazon & DPD · last 3 days · ${D.otp.webhook ? "also posted to your Discord" : "add OTP_WEBHOOK_URL to post to Discord"}</div></div></div>
        ${otpCards(D.otp.codes || [], false)}
      </div>
      <div class="grid">
        <div class="span-4">${kpi({ label: "High priority", value: all.filter((x) => x.priority === 1).length, foot: `${all.filter((x) => x.priority === 1 && x.unread).length} unread`, ic: "alert", tint: "red" })}</div>
        <div class="span-4">${kpi({ label: "Worth a look", value: all.filter((x) => x.priority > 1).length, foot: "medium & low", ic: "note", tint: "amber" })}</div>
        <div class="span-4">${kpi({ label: "Has a date", value: all.filter((x) => x.calendarUrl).length, foot: "one click to add to calendar", ic: "calendar", tint: "green" })}</div>
        <div class="card span-12">
          <div class="card-head"><div class="seg deal-filter">${cats.map((c) => `<button class="${c === impFilter ? "on" : ""}" data-imp-filter="${esc(c)}">${esc(c)}${c !== "All" ? ` · ${c === "High" ? all.filter((x) => x.priority === 1).length : all.filter((x) => x.category === c).length}` : ""}</button>`).join("")}</div></div>
          ${shown.length ? `<div class="imp-list">${shown.map(impCard).join("")}</div>` : `<div class="empty">Nothing here — you're on top of it ✓</div>`}
        </div>
      </div>`;
  };

  async function loadImportant(force) {
    let d;
    try { d = await (await fetch("/api/important" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    D.important = d;
    const nav = document.querySelector('.nav-item[href="#important"] .count');
    const high = impItems().filter((x) => x.priority === 1).length;
    if (nav) { nav.textContent = high || ""; nav.style.display = high ? "" : "none"; nav.classList.toggle("hot", impItems().some((x) => x.priority === 1 && x.unread)); }
    buildTicker();
    const h = location.hash.slice(1) || "overview";
    if (h === "important" || h === "overview") render();
    if (d.loading) setTimeout(loadImportant, 5000);
  }
  D.important = { loading: true };
  loadImportant();
  setInterval(loadImportant, 3 * 60 * 1000);
  document.addEventListener("click", (e) => {
    const f = e.target.closest("[data-imp-filter]");
    if (f) { impFilter = f.dataset.impFilter; render(); }
    const done = e.target.closest("[data-imp-done]");
    if (done) {
      const it = (D.important.items || []).find((x) => x.id === done.dataset.impDone);
      if (it) it.done = true;
      render();
      fetch("/api/important/done", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: done.dataset.impDone, groupKey: done.dataset.impGroup }) }).then(() => loadImportant());
    }
    if (e.target.closest("#impRestore")) {
      try { localStorage.removeItem(impDoneKey); } catch {}
      fetch("/api/important/done", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ restore: true }) }).then(() => loadImportant());
    }
    if (e.target.closest("#impRefresh")) { fetch("/api/important?refresh=1").then(() => setTimeout(loadImportant, 8000)); }
  });

  // ---------- Delivery codes (Amazon / DPD OTPs) ----------
  const destInfo = { Prep: { label: "PREP centre", tint: "amber", emoji: "🏭" }, Me: { label: "YOU · home", tint: "green", emoji: "🏠" }, Unknown: { label: "Check address", tint: "accent", emoji: "❓" } };

  function otpCards(codes, compact) {
    if (!codes.length) return `<div class="empty">No delivery codes in the last 3 days</div>`;
    return `<div class="otp-grid">${codes.map((c) => {
      const d = destInfo[c.dest] || destInfo.Unknown;
      return `
        <div class="otp-card dest-${(c.dest || "Unknown").toLowerCase()} ${c.today ? "today urgent" : ""}">
          <div class="row-flex" style="justify-content:space-between;gap:8px;flex-wrap:wrap">
            <span class="chip tint-${d.tint}">${d.emoji} ${d.label}</span>
            <span class="cell-sub">${esc(c.carrier)} · ${relTime(c.received)}</span>
          </div>
          <div class="otp-code" title="Click to copy" data-copy="${esc(c.code)}">${esc(c.code)}</div>
          <div class="list-meta">${c.window ? "🕑 " + esc(c.window) + " · " : ""}${esc(c.item || c.subject)}</div>
          ${compact ? "" : `<div class="list-meta">${c.order ? "Order " + esc(c.order) + " · " : ""}${c.parcel ? "Parcel " + esc(c.parcel) + " · " : ""}sent to ${esc(c.to || c.account)}</div>`}
          <div class="row-flex" style="gap:8px;margin-top:10px">
            <button class="btn primary" data-copy="${esc(c.code)}">${icon("note")}Copy code</button>
            ${c.posted ? '<span class="chip tint-green">Sent to Discord</span>' : ""}
          </div>
        </div>`;
    }).join("")}</div>`;
  }

  async function loadOtp(force) {
    let d;
    try { d = await (await fetch("/api/otp" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    const before = (D.otp && !D.otp.loading ? (D.otp.codes || []).map((c) => c.id).join() + D.otp.webhook : null);
    D.otp = d;
    const after = (d.codes || []).map((c) => c.id).join() + d.webhook;
    const h = location.hash.slice(1) || "overview";
    if (before !== after && (h === "overview" || h === "important")) render();
    if (d.loading) setTimeout(loadOtp, 5000);
  }
  D.otp = { loading: true, codes: [] };
  loadOtp();
  setInterval(loadOtp, 60 * 1000);
  document.addEventListener("click", async (e) => {
    const c = e.target.closest("[data-copy]");
    if (!c) return;
    try { await navigator.clipboard.writeText(c.dataset.copy); } catch {}
    const btn = c.tagName === "BUTTON" ? c : c.closest(".otp-card")?.querySelector("button[data-copy]");
    if (btn) { const old = btn.innerHTML; btn.textContent = "Copied ✓"; setTimeout(() => (btn.innerHTML = old), 1500); }
  });

  // ---------- Router ----------
  function countUp(root) {
    root.querySelectorAll(".kpi-value, .hero-value, .stage-n, .monitor-stats b").forEach((el) => {
      if (el.children.length) return;
      const m = el.textContent.match(/^([^\d-]*)(-?[\d,]+(?:\.\d+)?)(.*)$/s);
      if (!m) return;
      const [, pre, numStr, post] = m, target = parseFloat(numStr.replace(/,/g, "")), dp = (numStr.split(".")[1] || "").length;
      const t0 = performance.now(), dur = 900;
      const step = (t) => {
        const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        el.textContent = pre + (target * e).toLocaleString("en-GB", { minimumFractionDigits: dp, maximumFractionDigits: dp }) + post;
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  let lastView = null, forceAnim = false;
  function render() {
    const id = (location.hash.slice(1).split("?")[0] || "overview");
    const view = views[id] ? id : "overview";
    // Re-rendering the page you're on (data refresh, filter click) stays still: no replayed entrances, no scroll jump
    const quiet = view === lastView && !forceAnim;
    lastView = view; forceAnim = false;
    renderNav(view);
    charts.length = 0;
    const v = $("#view");
    const y = window.scrollY;
    const before = quiet ? snapshotNumbers(v) : null;
    v.classList.toggle("quiet", quiet);
    v.innerHTML = views[view]();
    v.querySelectorAll(".card").forEach((c, i) => c.style.setProperty("--i", i));
    drawCharts();
    if (!quiet) countUp(v); else rollNumbers(v, before);
    v.querySelectorAll(NUM_SEL).forEach((el) => el.classList.add("holo"));
    if (window.FX) FX.after(v, quiet);
    $("#sidebar").classList.remove("open");
    window.scrollTo({ top: quiet ? y : 0 });
  }

  let firstRender = true, leaveT;
  function route() {
    if (firstRender) { firstRender = false; return render(); }
    const v = $("#view");
    renderNav((location.hash.slice(1) || "overview"));
    v.classList.add("leaving");
    clearTimeout(leaveT);
    leaveT = setTimeout(() => { forceAnim = true; render(); v.classList.remove("leaving"); }, 170);
  }
  window.addEventListener("hashchange", route);
  let resizeT;
  window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(drawCharts, 120); });
  window.addEventListener("themechange", () => drawCharts());

  // Segmented buttons (visual only in the preview) + note selection
  document.addEventListener("click", (e) => {
    const b = e.target.closest(".seg button");
    if (b) { b.parentElement.querySelectorAll("button").forEach((x) => x.classList.remove("on")); b.classList.add("on"); }
    const note = e.target.closest("[data-note]");
    if (note) { activeNote = +note.dataset.note; route(); }
  });

  // ---------- Ask bar: answers questions from the dashboard's own data ----------
  const ASK_RE = /\?|^(what|whats|what's|how|which|when|where|who|show|any|do i|did|is|are|tell|give|list|my|how's|hows)\b/i;
  function askAnswer(q) {
    if (!q || q.length < 3 || !ASK_RE.test(q)) return null;
    const has = (re) => re.test(q);
    const ol = (arr) => `<ol>${arr.map((x) => `<li>${x}</li>`).join("")}</ol>`;
    const f = D.fba, live = D.fbaLive;
    const period = has(/yesterday/) ? "yesterday" : has(/month|mtd/) ? "month" : has(/30|last month|thirty/) ? "d30" : "today";
    const periodName = { today: "today", yesterday: "yesterday", month: "this month", d30: "in the last 30 days" }[period];

    if (has(/best|top/) && has(/sell|product|item|asin|earner/)) {
      const top = (f.topProducts || []).slice(0, 3);
      if (!top.length) return { a: "No product data yet. Invenno needs to be connected.", go: "#fba" };
      return { a: `Your top sellers by profit (last 30 days):${ol(top.map((p) => `<b>${esc(p.title.slice(0, 60))}</b>: ${gbp(p.profit)} profit, ${p.units} units`))}`, go: "#fba" };
    }
    if (has(/profit|made|make|earn|sales|revenue|sold|units|margin|fba|amazon/)) {
      if (!live) return { a: "Sales figures are offline. Invenno needs you to log in again (connect-invenno.bat).", go: "#fba" };
      const p = f[period] || {};
      return { a: `${periodName[0].toUpperCase() + periodName.slice(1)}: <b>${gbp(p.profit)}</b> profit on <b>${gbp(p.sales)}</b> sales${p.units != null ? `, <b>${p.units}</b> units` : ""}${p.margin != null ? `, ${Number(p.margin).toFixed(1)}% margin` : ""}.`, go: "#fba" };
    }
    if (has(/isa|vanguard|portfolio|shares|invest|stocks/)) {
      const i = D.isa;
      return { a: `ISA is worth <b>${gbp(i.value)}</b>, ${i.dayChangePct >= 0 ? "up" : "down"} <b>${Math.abs(i.dayChangePct).toFixed(2)}%</b> today${i.return != null ? `, total return <b>${gbp(i.return)}</b>` : ""}.`, go: "#isa" };
    }
    if (has(/lead|deal|flip|arbitrage|buy/)) {
      const open = (D.deals.leads || []).filter((l) => isProfitLead(l) && !l.status);
      const best = [...open].sort((a, b) => (b.profit || 0) - (a.profit || 0)).slice(0, 3);
      return { a: `<b>${open.length}</b> open profit leads.${best.length ? " Best by profit:" + ol(best.map((l) => `<b>${esc(l.title.slice(0, 55))}</b>: ${gbp(l.profit)}${l.roi != null ? ` · ${l.roi}% ROI` : ""} (${esc(l.source)})`)) : ""}`, go: "#deals" };
    }
    if (has(/code|otp|pin|parcel|deliver/)) {
      const codes = (D.otp.codes || []).filter((c) => c.today);
      return { a: codes.length ? `Today's delivery codes:${ol(codes.map((c) => `<b>${esc(c.code)}</b>: ${esc(c.carrier)} → ${esc(c.dest || "check")}`))}` : "No delivery codes today.", go: "#important" };
    }
    if (has(/email|mail|inbox|urgent|important/)) {
      if (!D.important || !D.important.configured) return { a: "Email isn't connected yet.", go: "#important" };
      const hi = impItems().filter((x) => x.priority === 1);
      return { a: hi.length ? `<b>${hi.length}</b> high-priority emails:${ol(hi.slice(0, 4).map((x) => `<b>${esc(x.subject.slice(0, 60))}</b> · ${esc(x.reason)}`))}` : "No high-priority emails. You're on top of it.", go: "#important" };
    }
    if (has(/claim|reclaim|reimburs|leak/)) {
      const items = actionItems();
      const r = D.reclaim && D.reclaim.dashboard;
      return { a: r ? `<b>${gbp(r.atRisk14)}</b> at risk in the next 14 days, <b>${items.length}</b> actions waiting.${items.length ? ol(items.slice(0, 3).map((a) => `${esc(a.verb)}: <b>${esc(a.title.slice(0, 50))}</b>${a.days != null ? ` (${a.days}d left)` : ""}`)) : ""}` : "ReclaimHQ data isn't loaded yet.", go: "#claims" };
    }
    if (has(/job|application|applied|interview|assessment|graduate/)) {
      const j = D.jobs;
      return { a: `<b>${j.matches.length}</b> top job matches, <b>${j.appliedThisWeek ?? 0}</b> applied this week, <b>${(j.followUps || []).length}</b> in process.`, go: "#jobs" };
    }
    if (has(/stock|inventory|restock|out of/)) {
      const al = (f.alerts || []).slice(0, 4);
      return { a: al.length ? `Stock alerts:${ol(al.map((x) => `<b>${esc(x.title)}</b>${x.meta ? " · " + esc(x.meta) : ""}`))}` : "No stock alerts.", go: "#fba" };
    }
    if (has(/calendar|today|tomorrow|next|schedule|event|deadline|plan|week|busy|free/)) {
      const day = has(/tomorrow/) ? 1 : 0;
      const evs = (D.calendar || []).filter((e) => has(/week/) ? e.d >= 0 && e.d < 7 : e.d === day);
      return { a: evs.length ? `${has(/week/) ? "This week" : day ? "Tomorrow" : "Today"}:${ol(evs.slice(0, 6).map((e) => `${e.t ? `<b>${e.t}</b> ` : ""}${esc(e.title)}`))}` : `Nothing in the calendar ${day ? "tomorrow" : "today"}.`, go: "#calendar" };
    }
    return { a: "I can answer about profit, sales, best sellers, stock, ISA, leads, emails, delivery codes, claims, jobs and your calendar. Try <b>\"what's my profit this month?\"</b>" };
  }

  // ---------- Voice greeting (first open each day, browser speech) ----------
  const voiceKey = "cc-voice", voiceDayKey = "cc-voice-day";
  const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
  const voiceOn = () => store.get(voiceKey) !== "off" && "speechSynthesis" in window;
  function speakBrief() {
    if (!("speechSynthesis" in window)) return;
    const tmp = document.createElement("div");
    tmp.innerHTML = aiBrief();
    // say "£478.86" naturally
    const said = [...tmp.querySelectorAll(".brief-text")].map((x) => x.textContent.replace(/£([\d,]+)\.(\d\d)/g, (_, a, b) => `${a} pounds ${b}`).replace(/£([\d,]+)/g, "$1 pounds"));
    const text = `${greeting()}${D.user.name ? ", " + D.user.name : ""}. Here's your brief. ${said.join(" ")}`;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const vs = speechSynthesis.getVoices();
    u.voice = vs.find((v) => /Sonia|Libby|Google UK English Female/i.test(v.name)) || vs.find((v) => v.lang === "en-GB") || null;
    u.rate = 1.02; u.pitch = 1;
    speechSynthesis.speak(u);
  }
  function maybeGreet() {
    const today = new Date().toDateString();
    if (!voiceOn() || store.get(voiceDayKey) === today) return;
    // Browsers only allow speech after you interact with the page, so greet on the first click/key of the day
    const go = () => {
      document.removeEventListener("pointerdown", go, true); document.removeEventListener("keydown", go, true);
      if (store.get(voiceDayKey) === today || !voiceOn()) return;
      store.set(voiceDayKey, today);
      setTimeout(speakBrief, 300);
    };
    document.addEventListener("pointerdown", go, true); document.addEventListener("keydown", go, true);
  }
  function voiceButton() {
    const b = $("#voiceBtn");
    if (!b) return;
    b.classList.toggle("on", voiceOn());
    b.title = voiceOn() ? "Voice brief on: click to hear it, right-click to mute" : "Voice brief muted: click to turn on";
  }
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#voiceBtn")) return;
    if (!voiceOn()) { store.set(voiceKey, "on"); voiceButton(); }
    if (speechSynthesis.speaking) speechSynthesis.cancel(); else speakBrief();
  });
  document.addEventListener("contextmenu", (e) => {
    if (!e.target.closest("#voiceBtn")) return;
    e.preventDefault(); speechSynthesis.cancel(); store.set(voiceKey, voiceOn() ? "off" : "on"); voiceButton();
  });
  setTimeout(() => { voiceButton(); maybeGreet(); }, 0);

  // ---------- Theme menu ----------
  function themeMenu() {
    const m = $("#themeMenu");
    if (!m || !window.FX) return;
    const cur = document.documentElement.getAttribute("data-theme") || "nebula";
    m.innerHTML = FX.themes.map((t) => `<button class="theme-opt ${t.id === cur ? "on" : ""}" data-theme="${t.id}"><span class="theme-sw" style="background:${t.sw}"></span>${t.name}</button>`).join("");
  }
  document.addEventListener("click", (e) => {
    const m = $("#themeMenu");
    if (!m) return;
    if (e.target.closest("#themeBtn")) { themeMenu(); m.classList.toggle("open"); return; }
    const opt = e.target.closest(".theme-opt");
    if (opt) { FX.setTheme(opt.dataset.theme, true); m.classList.remove("open"); return; }
    if (!e.target.closest("#themeMenu")) m.classList.remove("open");
  });

  // ---------- Live activity feed ----------
  const seenFeed = new Set();
  let feedSig = "";
  function feedEvents() {
    const ev = [];
    (D.dealsLive ? D.deals.leads : []).filter((l) => isProfitLead(l) && l.time && l.time.includes("T")).slice(0, 25).forEach((l) =>
      ev.push({ t: l.time, k: "lead", tag: `LEAD/${l.source}`, text: `${l.title.slice(0, 60)} ${l.profit != null ? "+" + gbp(l.profit) : ""}`, href: "#deals", id: "l" + l.key }));
    if (D.important && D.important.items) D.important.items.slice(0, 20).forEach((x) =>
      ev.push({ t: x.received, k: x.priority === 1 ? "hot" : "mail", tag: x.priority === 1 ? "MAIL/HIGH" : "MAIL", text: x.subject.slice(0, 52), href: "#important", id: "m" + x.id }));
    (D.otp.codes || []).forEach((c) => ev.push({ t: c.received, k: "code", tag: `OTP/${(c.dest || "check").toUpperCase()}`, text: `${c.carrier} code ${c.code}`, href: "#important", id: "o" + c.code + c.received }));
    if (D.fbaLive && D.fbaStatus.updated) ev.push({ t: new Date().toISOString().slice(0, 10) + "T" + (D.fbaStatus.updated.match(/\d\d:\d\d/) || ["00:00"])[0], k: "lead", tag: "Sales", text: `sync · ${gbp(D.fba.today.profit)} profit today`, href: "#fba", id: "fba" + D.fbaStatus.updated });
    return ev.filter((e) => e.t && !isNaN(new Date(e.t))).sort((a, b) => new Date(b.t) - new Date(a.t)).slice(0, 30);
  }
  function renderFeed() {
    let el = $("#feed");
    if (!el) {
      el = document.createElement("div");
      el.id = "feed"; el.className = "feed" + (store.get("cc-feed") === "collapsed" ? " collapsed" : "");
      el.innerHTML = `<div class="feed-head"><span class="dot"></span>Activity stream<span class="chev">▾</span></div><div class="feed-body"></div>`;
      $("#sidebar").insertBefore(el, $("#sidebar .sidebar-foot"));
      el.querySelector(".feed-head").addEventListener("click", () => { el.classList.toggle("collapsed"); store.set("cc-feed", el.classList.contains("collapsed") ? "collapsed" : "open"); });
    }
    const evs = feedEvents();
    const sig = evs.map((e) => e.id).join("|");
    if (sig === feedSig) return;
    const first = !feedSig; feedSig = sig;
    const hhmm = (t) => { const d = new Date(t); const today = d.toDateString() === new Date().toDateString(); return today ? d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }); };
    el.querySelector(".feed-body").innerHTML = evs.length ? evs.map((e) => {
      const isNew = !first && !seenFeed.has(e.id);
      seenFeed.add(e.id);
      return `<div class="feed-row ${isNew ? "new" : ""}"><span class="ft">${hhmm(e.t)}</span><span class="fk ${e.k}">${esc(e.tag)}</span><a href="${e.href}">${esc(e.text)}</a></div>`;
    }).join("") : `<div class="feed-row"><span class="ft">--:--</span><span>› waiting for signals…</span></div>`;
  }
  setInterval(renderFeed, 4000);
  setTimeout(renderFeed, 1500);

  // ---------- Odometer: numbers roll to their new value on data refreshes ----------
  const NUM_SEL = ".hero-value, .kpi-value, .stage-n, .monitor-stats b";
  function snapshotNumbers(root) { return [...root.querySelectorAll(NUM_SEL)].map((el) => el.textContent); }
  function rollNumbers(root, before) {
    const els = [...root.querySelectorAll(NUM_SEL)];
    if (els.length !== before.length) return;
    const num = (t) => { const m = /-?[\d,]+(?:\.\d+)?/.exec(t); return m ? parseFloat(m[0].replace(/,/g, "")) : null; };
    els.forEach((el, i) => {
      const oldT = before[i], newT = el.textContent;
      if (oldT === newT || el.children.length) return;
      const a = num(oldT), b = num(newT);
      if (a === null || b === null) return;
      el.classList.remove("num-up", "num-down");
      void el.offsetWidth;
      el.classList.add(b >= a ? "num-up" : "num-down");
      if (oldT.length !== newT.length) return; // width changed: just flash
      // Same width: roll each changed digit like an odometer
      el.innerHTML = [...newT].map((ch, k) => {
        const o = oldT[k];
        if (o === ch || !/\d/.test(ch) || !/\d/.test(o)) return esc(ch);
        const up = b >= a;
        return `<span class="odo"><span class="odo-in ${up ? "up" : "down"}"><span>${up ? o : ch}</span><span>${up ? ch : o}</span></span></span>`;
      }).join("");
      setTimeout(() => { if (el.querySelector(".odo")) el.textContent = newT; }, 1100);
    });
  }

  // ---------- Live system HUD ----------
  const HUD_SOURCES = [
    { key: "fba", label: "Sales", every: 15, go: "#fba" },
    { key: "monitors", label: "Monitors", every: 2, go: "#deals" },
    { key: "important", label: "Gmail", every: 10, go: "#important" },
    { key: "otp", label: "OTP", every: 1.5, go: "#important" },
    { key: "calendar", label: "Calendar", every: 10, go: "#calendar" },
    { key: "reclaim", label: "Reclaim", every: 30, go: "#claims" },
    { key: "jobs", label: "Jobs", every: 15, go: "#jobs" },
    { key: "isa", label: "ISA", every: 10, go: "#isa" },
    { key: "purchases", label: "Purchases", every: 20, go: "#purchases" },
  ];
  let health = null;
  async function loadHealth() {
    try { health = await (await fetch("/api/health")).json(); } catch { health = { down: true }; }
    renderHud();
  }
  const ago = (iso) => {
    if (!iso) return "—";
    const s = Math.max(0, (Date.now() - new Date(iso)) / 1000);
    return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`;
  };
  function hudItems() {
    if (!health) return [];
    if (health.down) return [{ label: "Server", st: "err", age: "offline", go: "#overview" }];
    const items = HUD_SOURCES.map((s) => {
      const t = health.checked && health.checked[s.key];
      const mins = t ? (Date.now() - new Date(t)) / 60000 : Infinity;
      const st = health.errors && health.errors[s.key] ? "err" : !t ? "wait" : mins > s.every * 3 ? "warn" : "ok";
      return { label: s.label, st, age: ago(t), go: s.go, title: `${s.label}: last check ${t ? new Date(t).toLocaleTimeString("en-GB") : "pending"} · runs every ${s.every < 2 ? s.every * 60 + "s" : s.every + " min"}` };
    });
    (D.dealsLive ? D.deals.monitors : []).filter((m) => !m.manual).forEach((m) => items.push({
      label: m.store, st: !m.running ? "err" : m.status === "ok" ? "ok" : "warn", age: ago(m.lastActivity), go: "#deals", svc: true,
      title: `${m.name}: ${m.lastEvent || ""}`,
    }));
    return items;
  }
  function renderHud() {
    let el = $("#hud");
    if (!el) {
      el = document.createElement("div");
      el.id = "hud"; el.className = "hud";
      $(".main").insertBefore(el, $("#view"));
    }
    const items = hudItems();
    const bad = items.filter((x) => x.st === "warn" || x.st === "err").length;
    el.innerHTML = `<span class="hud-tag"><span class="dot ${bad ? "warn" : "ok"}"></span>SYS ${bad ? bad + " ALERT" + (bad > 1 ? "S" : "") : "NOMINAL"}</span>` +
      items.map((x) => `<a class="hud-item st-${x.st} ${x.svc ? "svc" : ""}" href="${x.go}" title="${esc(x.title || "")}"><i></i>${esc(x.label)}<b>${x.st === "wait" ? "…" : x.age}</b></a>`).join("") +
      (health && health.started ? `<span class="hud-up">UPTIME ${ago(health.started)}</span>` : "");
    const pill = $(".sidebar-foot .status-pill");
    if (pill) pill.innerHTML = `<span class="dot ${bad ? "warn" : "ok"}"></span>${bad ? `${bad} service${bad > 1 ? "s" : ""} need attention` : "All systems running"}`;
  }
  loadHealth();
  setInterval(loadHealth, 15000);
  setInterval(renderHud, 5000);

  // ---------- Desktop notifications ----------
  const NOTIFY_KEY = "cc-notify", SEEN_KEY = "cc-notified";
  const notifyOn = () => "Notification" in window && Notification.permission === "granted" && store.get(NOTIFY_KEY) !== "off";
  let seenN = new Set(); try { seenN = new Set(JSON.parse(store.get(SEEN_KEY) || "[]")); } catch {}
  let seeded = seenN.size > 0;
  function notifyCandidates() {
    const out = [];
    if (D.important && D.important.items) D.important.items.filter((x) => x.priority === 1 && x.unread).forEach((x) =>
      out.push({ id: "m" + x.id, title: `📧 ${x.reason}`, body: `${x.subject}\n${x.from}`, go: "#important" }));
    (D.otp.codes || []).filter((c) => c.today).forEach((c) =>
      out.push({ id: "o" + c.code + c.received, title: `📦 ${c.carrier} code ${c.code}`, body: `${(destInfo[c.dest] || destInfo.Unknown).label} · ${c.item || c.subject || ""}`, go: "#important" }));
    if (D.dealsLive) D.deals.leads.filter((l) => isProfitLead(l) && !l.status && ((l.profit || 0) >= 20 || ((l.roi || 0) >= 60 && (l.profit || 0) >= 5))).forEach((l) =>
      out.push({ id: "l" + l.key, title: `⚡ ${l.source} lead +${gbp(l.profit)}${l.roi != null ? ` · ${l.roi}% ROI` : ""}`, body: l.title, go: "#deals" }));
    return out;
  }
  function checkNotifications() {
    const cands = notifyCandidates();
    if (!cands.length) return;
    // First run: remember what's already there so you aren't flooded with old items
    if (!seeded) { cands.forEach((c) => seenN.add(c.id)); seeded = true; saveSeen(); return; }
    const fresh = cands.filter((c) => !seenN.has(c.id));
    fresh.forEach((c) => seenN.add(c.id));
    if (fresh.length) saveSeen();
    if (!notifyOn()) return;
    fresh.slice(0, 4).forEach((c) => {
      try {
        const n = new Notification(c.title, { body: c.body, tag: c.id, icon: "data:image/svg+xml," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='#6d6af7'/><path d='M9 16h14M16 9v14' stroke='white' stroke-width='3' stroke-linecap='round'/></svg>") });
        n.onclick = () => { window.focus(); location.hash = c.go; n.close(); };
      } catch {}
    });
    if (fresh.length > 4) try { new Notification(`+${fresh.length - 4} more alerts`, { body: "Open the Command Centre to see them all." }); } catch {}
  }
  function saveSeen() { store.set(SEEN_KEY, JSON.stringify([...seenN].slice(-600))); }
  function bellState() {
    const b = $(".topbar .has-badge");
    if (!b) return;
    b.id = "bellBtn";
    const urgent = (D.important && D.important.items ? D.important.items.filter((x) => x.priority === 1 && x.unread).length : 0) + (D.otp.codes || []).filter((c) => c.today).length;
    const badge = b.querySelector(".badge");
    if (badge) { badge.textContent = urgent; badge.style.display = urgent ? "" : "none"; }
    b.classList.toggle("on", notifyOn());
    b.title = !("Notification" in window) ? "Notifications not supported" : notifyOn() ? "Desktop alerts ON: click to turn off" : Notification.permission === "denied" ? "Desktop alerts blocked in the browser's site settings" : "Click to turn on desktop alerts";
  }
  document.addEventListener("click", async (e) => {
    if (!e.target.closest("#bellBtn")) return;
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") await Notification.requestPermission();
    else if (Notification.permission === "granted") store.set(NOTIFY_KEY, notifyOn() ? "off" : "on");
    if (notifyOn()) try { new Notification("Desktop alerts on ✓", { body: "You'll get urgent emails, delivery codes and big leads while the dashboard is open." }); } catch {}
    bellState();
  });
  setInterval(() => { checkNotifications(); bellState(); }, 15000);
  setTimeout(() => { checkNotifications(); bellState(); }, 9000);

  // ---------- Weekly recap (shows from Monday until dismissed) ----------
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  function lastWeek() {
    const t = new Date(); t.setHours(0, 0, 0, 0);
    const mon = new Date(t); mon.setDate(t.getDate() - ((t.getDay() + 6) % 7) - 7);
    const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
    return { mon, sun, key: iso(mon) };
  }
  D.recap = null;
  async function loadRecap() {
    const w = lastWeek();
    if (store.get("cc-recap-dismissed") === w.key) return;
    try {
      const r = await (await fetch(`/api/fba/range?from=${iso(w.mon)}&to=${iso(w.sun)}`)).json();
      D.recap = { ...w, fba: r.current ? r : null };
    } catch { D.recap = { ...w, fba: null }; }
    if ((location.hash.slice(1) || "overview") === "overview") render();
  }
  function recapCard() {
    const R = D.recap;
    if (!R) return "";
    const end = new Date(R.sun); end.setHours(23, 59, 59);
    const inWeek = (t) => { if (!t) return false; const d = new Date(t); return d >= R.mon && d <= end; };
    const f = R.fba && R.fba.current, ch = R.fba && R.fba.change;
    const best = R.fba && (R.fba.topProducts || [])[0];
    const leads = D.dealsLive ? D.deals.leads.filter((l) => isProfitLead(l) && inWeek(l.time)) : [];
    const bought = D.dealsLive ? D.deals.leads.filter((l) => l.status === "bought" && inWeek(l.statusAt)) : [];
    let apps = null;
    if (D.jobs && D.jobs.applied30) {
      const n = D.jobs.applied30.length; apps = 0;
      D.jobs.applied30.forEach((v, i) => { const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() - (n - 1 - i)); if (d >= R.mon && d <= end) apps += v; });
    }
    const rec = D.reclaim && D.reclaim.dashboard ? D.reclaim.dashboard.recovered30 : null;
    const fmtD = (d) => d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    const tile = (label, value, sub = "") => `<div class="recap-tile"><div class="cell-sub">${label}</div><div class="recap-v">${value}</div>${sub ? `<div class="cell-sub">${sub}</div>` : ""}</div>`;
    return `
      <div class="card recap span-12">
        <div class="card-head"><div><div class="eyebrow" style="color:var(--accent)">Weekly recap</div><div class="card-title">${fmtD(R.mon)} – ${fmtD(R.sun)}</div></div>
          <button class="icon-btn" id="recapDismiss" title="Dismiss until next Monday" aria-label="Dismiss">✕</button></div>
        <div class="recap-grid">
          ${f ? tile("Profit", gbp(f.profit), ch && ch.profit != null ? deltaSpan(ch.profit).replace(" vs previous period", " vs week before") : "") : tile("Profit", "—", "Invenno offline")}
          ${f ? tile("Sales", gbp(f.sales), `${f.units} units · ${f.margin != null ? f.margin.toFixed(1) + "% margin" : ""}`) : ""}
          ${best ? tile("Best seller", esc(best.title.split(/[|,–-]/)[0].trim().slice(0, 34)), `${gbp(best.profit)} profit · ${best.units} units`) : ""}
          ${tile("Leads", `${leads.length}`, `${bought.length} bought`)}
          ${apps != null ? tile("Applications", `${apps}`, "sent that week") : ""}
          ${rec != null ? tile("Claims recovered", gbp(rec), "last 30 days") : ""}
        </div>
      </div>`;
  }
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#recapDismiss")) return;
    store.set("cc-recap-dismissed", D.recap.key); D.recap = null; render();
  });
  setTimeout(loadRecap, 2500);

  // ---------- Purchases tracker (order emails + Invenno + prep centre) ----------
  D.purchases = { loading: true };
  let purFilter = "All", purQuery = "", purNoteEdit = null;
  const PUR_STAGES = [
    ["ordered", "Ordered", "cart"], ["shipped", "In transit", "trend"], ["delivered", "Delivered", "box"],
    ["atprep", "At prep", "clock"], ["prepped", "Prepped", "shield"], ["sent", "Sent to Amazon", "ext"],
    ["live", "Live", "bolt"], ["cancelled", "Cancelled", "alert"],
  ];
  const curFmt = (n, c) => n == null ? "" : (c === "€" ? "€" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : gbp(n));
  function purCard(c) {
    const p = c.inv, probs = c.problems || [];
    const urgent = probs.some((x) => x.type !== "notinvenno") && c.stage !== "cancelled";
    const dk = c.dest === "Prep" ? "prep" : c.dest === "Me" ? "home" : "unk";
    const dest = `<span class="pur-dest d-${dk}">${{ prep: "🏭 PREP centre", home: "🏠 HOME", unk: "📍 Destination unknown" }[dk]}</span>`;
    const editing = purNoteEdit === c.id;
    const note = editing
      ? `<div class="pur-note-edit"><textarea data-note-key="${esc(c.id)}" rows="3" placeholder="Card used, coupon, chased Amazon, refund pending…">${esc(c.userNote || "")}</textarea>
           <div class="row-flex" style="gap:6px;margin-top:5px"><button class="mini-btn ok" data-note-save="${esc(c.id)}">Save</button><button class="mini-btn" data-note-cancel>Cancel</button></div></div>`
      : c.userNote ? `<div class="pur-note" data-note-open="${esc(c.id)}" title="Click to edit">📝 ${esc(c.userNote)}</div>`
      : `<button class="pur-note-add" data-note-open="${esc(c.id)}">📝 Add note</button>`;
    const prog = p ? `<div class="pur-prog">
        <span title="Received at prep">📥 ${p.received}/${p.qty}</span><span title="Prepped">🧰 ${p.prepped}</span><span title="Sent to Amazon">🚚 ${p.sent}</span>${p.live ? `<span title="Live at Amazon (fulfillable)">🟢 ${p.live}</span>` : ""}
        ${p.prepStatus ? `<span class="cell-sub">${esc(p.prepStatus)}</span>` : ""}</div>` : "";
    return `<div class="pur-card dest-${dk} ${urgent ? "urgent" : ""} ${c.untracked ? "untracked" : ""}">
      ${dest}
      <div class="row-flex" style="gap:6px;margin-top:6px"><span class="chip src">${esc(c.source)}</span></div>
      <div class="pur-title" title="${esc(c.title)}">${c.qty ? `<b>${c.qty}×</b> ` : ""}${esc(c.title)}${c.moreItems ? ` <span class="cell-sub">+${c.moreItems} more</span>` : ""}</div>
      <div class="pur-meta">${c.total != null ? `<span>${curFmt(c.total, c.currency)}</span>` : ""}<span>${relTime(c.orderedAt)}</span>${c.eta && ["ordered", "shipped"].includes(c.stage) ? `<span>ETA ${esc(c.eta)}</span>` : ""}${c.delayed ? `<span class="down">delayed</span>` : ""}${c.pendingPayment && c.stage === "ordered" ? `<span class="cell-sub">payment pending</span>` : ""}</div>
      ${prog}
      ${c.note ? `<div class="cell-sub" style="margin-top:4px">${esc(c.note)}</div>` : ""}
      ${probs.map((x) => `<div class="pur-prob t-${x.type}">${{ cancelled: "❌", missing: "⚠️", stuck: "⏳", notinvenno: "❓", money: "💳" }[x.type]} ${esc(x.text)}</div>`).join("")}
      ${c.payment ? `<div class="pur-paid">💳 Paid ${gbp(c.payment.amount)} · ${esc(c.payment.source)} · ${esc(c.payment.date)}</div>` : ""}
      ${c.link ? `<a class="link pur-link" href="${esc(c.link)}" target="_blank" rel="noopener">Order ${esc(c.order)} ↗</a>` : c.order ? `<div class="cell-sub">Order ${esc(c.order)}</div>` : ""}
      ${note}
    </div>`;
  }
  views.purchases = () => {
    const P = D.purchases || {};
    const head = pageHead("Purchases", P.updated ? `Order emails + Invenno + prep centre · open orders and last ${P.days || 30} days · updated ${P.updated}` : "Every order from ordered to live at Amazon",
      `<button class="btn" id="purRefresh">${icon("refresh")}Refresh</button>`);
    if (P.loading || P.configured === null) return head + `<div class="banner ok">${icon("refresh")}Reading your order emails and Invenno purchases… (first run takes a couple of minutes)</div>`;
    if (!P.configured) return head + `<div class="banner">${icon("alert")}<span>Connect a Gmail app password to switch this on.</span></div>`;
    const S = P.summary || {}, cards = P.cards || [];
    const q = purQuery.toLowerCase();
    const shown = cards.filter((c) => (purFilter === "All" || (purFilter === "Problems" ? (c.problems || []).length && c.stage !== "cancelled" : purFilter === "Prep" ? c.dest === "Prep" : purFilter === "Home" ? c.dest === "Me" : c.source === purFilter))
      && (!q || (c.title + " " + (c.order || "") + " " + c.source).toLowerCase().includes(q)));
    const sources = [...new Set(cards.map((c) => c.source))].sort();
    const probCount = cards.filter((c) => (c.problems || []).length && c.stage !== "cancelled").length;
    return `${head}
      ${(P.errors || []).map((e) => `<div class="banner">${icon("alert")}<span>${esc(e)}</span></div>`).join("")}
      <div class="grid">
        <div class="span-3">${kpi({ label: `Spent · ${P.days || 30} days`, value: gbp(S.spendGBP, 0), foot: `${S.orders ?? "—"} orders · ${S.units ?? "—"} units`, ic: "pound", tint: "accent" })}</div>
        <div class="span-3">${kpi({ label: "At prep", value: `${S.unitsReceived ?? 0} recv`, foot: `${S.unitsPrepped ?? 0} prepped · ${S.missing ?? 0} with missing units`, ic: "box", tint: "amber" })}</div>
        <div class="span-3">${kpi({ label: "Sent to Amazon", value: `${S.unitsSent ?? 0} units`, foot: `${(S.byStage || {}).live ?? 0} lines live`, ic: "ext", tint: "green" })}</div>
        <div class="span-3">${kpi({ label: "Needs attention", value: `${probCount}`, foot: `${S.cancelled ?? 0} cancelled in ${P.days || 30} days`, ic: "alert", tint: probCount ? "red" : "green" })}</div>
      </div>
      <div class="card" style="margin-top:16px;padding:14px 16px">
        <div class="row-flex" style="gap:10px;flex-wrap:wrap;justify-content:space-between">
          <div class="seg pur-filter">${["All", "Problems", "Prep", "Home", ...sources].map((f) => `<button class="${f === purFilter ? "on" : ""}" data-pur-filter="${esc(f)}">${{ Prep: "🏭 Prep", Home: "🏠 Home" }[f] || esc(f)}${f === "Problems" ? " · " + probCount : f === "Prep" ? " · " + cards.filter((c) => c.dest === "Prep" && !["live", "cancelled"].includes(c.stage)).length : f === "Home" ? " · " + cards.filter((c) => c.dest === "Me" && !["live", "cancelled"].includes(c.stage)).length : ""}</button>`).join("")}</div>
          <input class="pur-search" id="purSearch" placeholder="Search item or order #" value="${esc(purQuery)}">
        </div>
      </div>
      <div class="pur-board">${PUR_STAGES.map(([id, label, ic]) => {
        const col = shown.filter((c) => c.stage === id).sort((a, b) => ((b.problems || []).length - (a.problems || []).length) || b.orderedAt.localeCompare(a.orderedAt));
        return `<div class="pur-col st-${id}"><div class="pur-col-head">${icon(ic)}<b>${label}</b><span class="count">${col.length}</span></div>
          <div class="pur-col-body">${col.slice(0, 80).map(purCard).join("") || `<div class="cell-sub" style="padding:8px">Nothing here</div>`}${col.length > 80 ? `<div class="cell-sub" style="padding:8px">+${col.length - 80} more · use search</div>` : ""}</div></div>`;
      }).join("")}</div>
      <div class="cell-sub" style="margin-top:10px">Stuck limits: Amazon EU ${P.limits?.eu_delivery}d, UK ${P.limits?.uk_delivery}d to deliver · ${P.limits?.prep}d at prep · ${P.limits?.send_in}d to send in. Reading: ${(P.accounts || []).map(esc).join(", ")}.</div>`;
  };
  async function loadPurchases(force) {
    let d;
    try { d = await (await fetch("/api/purchases" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    D.purchases = d;
    const n = (d.cards || []).filter((c) => (c.problems || []).length && c.stage !== "cancelled").length;
    const nav = document.querySelector('.nav-item[href="#purchases"] .count');
    if (nav) { nav.textContent = n || ""; nav.style.display = n ? "" : "none"; nav.classList.toggle("hot", n > 0); }
    if ((location.hash.slice(1) || "overview") === "purchases" && !purNoteEdit) render();
    if (d.loading || d.configured === null) setTimeout(loadPurchases, 15000);
  }
  document.addEventListener("click", (e) => {
    const f = e.target.closest("[data-pur-filter]");
    if (f) { purFilter = f.dataset.purFilter; render(); }
    const no = e.target.closest("[data-note-open]");
    if (no) { purNoteEdit = no.dataset.noteOpen; render(); setTimeout(() => { const t = document.querySelector(`[data-note-key="${CSS.escape(purNoteEdit)}"]`); if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }, 30); return; }
    if (e.target.closest("[data-note-cancel]")) { purNoteEdit = null; render(); return; }
    const ns = e.target.closest("[data-note-save]");
    if (ns) {
      const key = ns.dataset.noteSave, text = document.querySelector(`[data-note-key="${CSS.escape(key)}"]`).value;
      const c = (D.purchases.cards || []).find((x) => x.id === key); if (c) c.userNote = text.trim();
      purNoteEdit = null; render();
      fetch("/api/purchases/note", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key, text }) });
      return;
    }
    if (e.target.closest("#purRefresh")) { fetch("/api/purchases?refresh=1"); setTimeout(() => loadPurchases(), 60000); const b = e.target.closest("#purRefresh"); b.textContent = "Refreshing… (~1 min)"; }
  });
  document.addEventListener("input", (e) => {
    if (e.target.id === "purSearch") { purQuery = e.target.value; const pos = e.target.selectionStart; render(); const s = $("#purSearch"); if (s) { s.focus(); s.setSelectionRange(pos, pos); } }
  });
  loadPurchases();
  setInterval(loadPurchases, 5 * 60 * 1000);

  // ---------- Money: business spending (CSV exports + bank feeds), questions, matching ----------
  D.money = { loading: true };
  let bankMsg = null, bankQuery = "", moneyCat = "All";
  const gbp2 = (n) => (n < 0 ? "−" : "") + "£" + Math.abs(n).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  views.money = () => {
    const M = D.money || {};
    const head = pageHead("Money", "Business spending · last 90 days · Capital on Tap export" + ((M.files || []).length > 1 ? "s" : "") + (M.connections && M.connections.length && !M.sandbox ? " + bank feeds" : ""),
      `<a class="btn" href="/api/bank/connect">${icon("plus")}Connect bank</a><button class="btn" id="moneyRefresh">${icon("refresh")}Refresh</button>`);
    if (M.loading) return head + `<div class="banner ok">${icon("refresh")}Loading…</div>`;
    const T = M.transactions || [], Q = M.questions || [], cats = M.categories || [];
    // Transfers (card repayments, moving money between your own accounts) aren't spending
    const out = T.filter((t) => t.amount < 0 && t.cat !== "Transfers"), inn = T.filter((t) => t.amount > 0 && t.cat !== "Transfers");
    const spend = Object.fromEntries(Object.entries(M.spendByCategory || {}).filter(([k]) => k !== "Transfers")), maxSpend = Math.max(1, ...Object.values(spend));
    const q = bankQuery.toLowerCase();
    const shown = T.filter((t) => (moneyCat === "All" || (moneyCat === "Unsorted" ? !t.cat : t.cat === moneyCat)) && (!q || (t.description + " " + t.merchant + " " + t.source + " " + (t.order || "")).toLowerCase().includes(q)));
    const catOpts = (sel) => `<option value="">Choose…</option>` + cats.map((c) => `<option ${c === sel ? "selected" : ""}>${esc(c)}</option>`).join("");
    return `${head}
      ${bankMsg ? `<div class="banner ${/fail|cancel/i.test(bankMsg) ? "" : "ok"}">${icon("shield")}<span>${esc(bankMsg)}</span></div>` : ""}
      ${!(M.files || []).length ? `<div class="banner">${icon("alert")}<span>Drop your card/bank CSV exports into <code>Documents\\command-centre\\bank_exports</code>.</span></div>` : ""}
      <div class="grid">
        <div class="span-3">${kpi({ label: "Spent · 90 days", value: gbp2(out.reduce((a, t) => a + t.amount, 0)), foot: `${out.length} payments · repayments & transfers excluded`, ic: "cart", tint: "accent" })}</div>
        <div class="span-3">${kpi({ label: "Stock", value: gbp(spend.Stock || 0, 0), foot: `${M.matched || 0} payments matched to orders`, ic: "box", tint: "green" })}</div>
        <div class="span-3">${kpi({ label: "Needs your input", value: `${Q.length}`, foot: Q.length ? "answer below; I remember each merchant" : "all sorted ✓", ic: "alert", tint: Q.length ? "amber" : "green" })}</div>
        <div class="span-3">${kpi({ label: "Refunds & money in", value: gbp(inn.reduce((a, t) => a + t.amount, 0), 0), foot: `${inn.length} credits · card repayments & transfers excluded`, ic: "pound", tint: "blue" })}</div>

        ${Q.length ? `<div class="card span-12">
          <div class="card-head"><div><div class="card-title">❓ Needs your input</div><div class="card-sub">What were these for? Pick a category; I'll remember the merchant so you're only asked once.</div></div></div>
          <div class="list">${Q.map((x) => `<div class="list-item money-q">
            <span class="kpi-icon tint-amber">${icon("alert")}</span>
            <div class="list-body"><div class="list-title">${esc(x.merchant || x.description)} <span class="cell-sub">· ${esc(x.date)} · ${esc(x.source)}</span></div><div class="list-meta">${esc(x.question)}</div></div>
            <div class="list-right money-q-right"><b class="${x.amount < 0 ? "down" : "up"}">${gbp2(x.amount)}</b>
              <select class="money-sel" data-q-id="${esc(x.id)}" data-q-mk="${esc(x.merchantKey)}">${catOpts("")}</select></div>
          </div>`).join("")}</div>
        </div>` : ""}

        <div class="card span-5">
          <div class="card-head"><div><div class="card-title">Where the money went</div><div class="card-sub">90 days, by category</div></div></div>
          <div class="money-bars">${Object.entries(spend).map(([k, v]) => `<button class="money-bar ${moneyCat === (k === "Uncategorised" ? "Unsorted" : k) ? "on" : ""}" data-money-cat="${esc(k === "Uncategorised" ? "Unsorted" : k)}">
            <span class="mb-label">${esc(k)}</span><span class="mb-track"><i style="width:${Math.max(2, v / maxSpend * 100)}%"></i></span><b>${gbp(v, 0)}</b></button>`).join("")}</div>
        </div>
        <div class="card span-7">
          <div class="card-head"><div><div class="card-title">Purchases ↔ payments</div><div class="card-sub">From the Purchases tracker</div></div><a class="link" href="#purchases">Open Purchases</a></div>
          ${(() => {
            const C = (D.purchases && D.purchases.cards) || [];
            const flags = C.filter((c) => (c.problems || []).some((p) => p.type === "money"));
            return flags.length ? `<div class="list">${flags.slice(0, 8).map((c) => `<div class="list-item"><span class="kpi-icon tint-red">${icon("pound")}</span>
              <div class="list-body"><div class="list-title">${esc(c.source)} · ${c.qty}× ${esc((c.title || "").slice(0, 60))}</div><div class="list-meta">${c.problems.filter((p) => p.type === "money").map((p) => esc(p.text)).join(" · ")}</div></div>
              <div class="list-right cell-sub">${c.total != null ? (c.currency === "€" ? "€" + c.total : gbp(c.total)) : ""}</div></div>`).join("")}</div>` : `<div class="empty">No payment problems spotted ✓</div>`;
          })()}
        </div>

        <div class="card span-12 flush">
          <div class="card-head" style="padding:16px 18px 0;flex-wrap:wrap;gap:10px"><div><div class="card-title">Transactions</div><div class="card-sub">${shown.length} of ${T.length}${moneyCat !== "All" ? ` · ${esc(moneyCat)} <a class="link" href="#" data-money-cat="All">show all</a>` : ""}</div></div>
            <input class="pur-search" id="bankSearch" placeholder="Search merchant, card or order" value="${esc(bankQuery)}"></div>
          <div class="table-wrap"><table><thead><tr><th>Date</th><th>Merchant</th><th>Card</th><th>Category</th><th>Matched order</th><th class="num">Amount</th></tr></thead><tbody>
            ${shown.slice(0, 400).map((t) => `<tr><td class="mono">${esc(t.date)}</td>
              <td><div class="cell-main">${esc(t.merchant || t.description)}</div>${t.origCurrency && t.origCurrency !== "GBP" ? `<div class="cell-sub">${esc(Math.abs(t.origAmount).toFixed(2))} ${esc(t.origCurrency)}</div>` : ""}</td>
              <td class="cell-sub">${esc(t.source)}</td>
              <td><select class="money-sel sm" data-q-id="${esc(t.id)}" data-q-mk="${esc(t.merchantKey)}">${catOpts(t.cat || "")}</select>${t.catHow === "rule" ? `<div class="cell-sub">auto</div>` : t.catHow ? `<div class="cell-sub">${t.catHow === "you" ? "your answer" : t.catHow === "learned" ? "learned" : "matched"}</div>` : ""}</td>
              <td class="cell-sub" style="max-width:280px">${esc(t.order || t.note || "")}</td>
              <td class="num ${t.amount < 0 ? "down" : "up"}">${gbp2(t.amount)}</td></tr>`).join("") || `<tr><td colspan="6" class="empty">Nothing here</td></tr>`}
          </tbody></table></div>
        </div>
        ${M.sandbox ? `<div class="card span-12"><div class="card-sub">🧪 Bank feeds are in <b>test mode</b> (TrueLayer sandbox, Mock Bank: ${M.testSources} test accounts). Test data is kept out of these figures. Real Amex / Capital on Tap / Revolut feeds connect the same way once TrueLayer is switched to live.</div></div>` : ""}
      </div>`;
  };
  async function loadMoney() {
    try { D.money = await (await fetch("/api/money")).json(); } catch { return; }
    if ((location.hash.slice(1).split("?")[0] || "overview") === "money") render();
  }
  {
    const m = /[?&]msg=([^&]+)/.exec(location.hash);
    if (m) { bankMsg = decodeURIComponent(m[1]); history.replaceState(null, "", "#money"); }
  }
  document.addEventListener("click", (e) => {
    if (e.target.closest("#moneyRefresh")) { fetch("/api/bank?refresh=1"); loadMoney(); }
    const mc = e.target.closest("[data-money-cat]");
    if (mc) { e.preventDefault(); moneyCat = moneyCat === mc.dataset.moneyCat ? "All" : mc.dataset.moneyCat; render(); }
  });
  document.addEventListener("change", async (e) => {
    const s = e.target.closest(".money-sel");
    if (!s || !s.value) return;
    s.disabled = true;
    await fetch("/api/money/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: s.dataset.qId, category: s.value, merchantKey: s.dataset.qMk, remember: true }) });
    loadMoney();
  });
  document.addEventListener("input", (e) => {
    if (e.target.id === "bankSearch") { bankQuery = e.target.value; const pos = e.target.selectionStart; render(); const x = $("#bankSearch"); if (x) { x.focus(); x.setSelectionRange(pos, pos); } }
  });
  loadMoney();
  setInterval(loadMoney, 10 * 60 * 1000);

  // ---------- Insights: refund chaser, Monday digest, cash-flow estimate, stock ageing ----------
  D.insights = { loading: true };
  const money0 = (n) => n == null ? "—" : gbp(n, 0);
  function digestCard(g, compact) {
    if (!g) return "";
    const fmtD = (s) => new Date(s).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    const cats = Object.entries(g.spendByCategory || {}).slice(0, compact ? 4 : 8);
    return `<div class="card span-12 recap">
      <div class="card-head"><div><div class="eyebrow" style="color:var(--accent)">Monday money digest</div><div class="card-title">${fmtD(g.from)} – ${fmtD(g.to)}</div></div>${compact ? `<a class="link" href="#insights">Insights</a>` : ""}</div>
      <div class="recap-grid">
        <div class="recap-tile"><div class="cell-sub">Spent</div><div class="recap-v">${money0(g.spend)}</div><div class="cell-sub">${cats.map(([k, v]) => `${esc(k)} ${money0(v)}`).join(" · ") || "no exports for this week yet"}</div></div>
        <div class="recap-tile"><div class="cell-sub">Stock bought</div><div class="recap-v">${g.ordersPlaced} orders</div><div class="cell-sub">${g.unitsBought} units · ${money0(g.stockSpend)} (£ orders)</div></div>
        <div class="recap-tile"><div class="cell-sub">Amazon sales</div><div class="recap-v">${money0(g.sales)}</div><div class="cell-sub">${g.profit != null ? money0(g.profit) + " profit" : ""}</div></div>
        <div class="recap-tile"><div class="cell-sub">Needs you</div><div class="recap-v">${g.questions} questions</div><div class="cell-sub">${g.refundsOutstanding} refunds outstanding · ${g.stuck} stuck orders</div></div>
      </div></div>`;
  }
  views.insights = () => {
    const I = D.insights || {};
    const head = pageHead("Insights", "Refunds to chase · weekly digest · cash flow · stock ageing", `<button class="btn" id="insRefresh">${icon("refresh")}Refresh</button>`);
    if (I.loading) return head + `<div class="banner ok">${icon("refresh")}Working it out…</div>`;
    const ch = I.chaser || { due: [], waiting: [] }, cf = I.cashflow || {}, st = I.stock || {}, nl = I.notLive || [];
    const chaseRow = (x, due) => `<div class="list-item ${due ? "urgent" : ""}">
      <span class="kpi-icon tint-${due ? "red" : "amber"}">${icon("pound")}</span>
      <div class="list-body"><div class="list-title">${esc(x.source)} · ${x.qty || ""}× ${esc((x.title || "").slice(0, 70))}</div>
        <div class="list-meta">${x.problems.map(esc).join(" · ")}${x.order ? " · order " + esc(x.order) : ""} · flagged ${esc(x.firstSeen)}${x.chasedTimes ? ` · chased ${x.chasedTimes}× (last ${esc(x.lastChased)})` : ""}</div></div>
      <div class="list-right" style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
        ${x.link ? `<a class="mini-btn" href="${esc(x.link)}" target="_blank" rel="noopener">Open order ↗</a>` : ""}
        <button class="mini-btn" data-chase="${esc(x.key)}" data-act="chased">📞 Chased</button>
        <button class="mini-btn ok" data-chase="${esc(x.key)}" data-act="resolved">✅ Resolved</button>
        ${due ? "" : `<span class="cell-sub">due in ${x.dueIn}d</span>`}</div></div>`;
    const stockRow = (r) => `<tr><td><div class="cell-main" style="max-width:360px;overflow:hidden;text-overflow:ellipsis">${esc(r.title || r.asin)}</div><div class="cell-sub">${esc(r.sku)}</div></td>
      <td class="num">${r.stock}</td><td class="num">${r.age ?? "—"}d</td><td class="num">${r.sold30}</td><td class="num">${r.cost != null ? gbp(r.cost) : "—"}</td><td class="num"><b>${gbp(r.tiedUp)}</b></td></tr>`;
    const cards = Object.entries(cf.cards || {});
    return `${head}
      <div class="grid">
        <div class="span-3">${kpi({ label: "Refunds to chase now", value: `${ch.due.length}`, foot: `${ch.waiting.length} more waiting (<${ch.days}d)`, ic: "alert", tint: ch.due.length ? "red" : "green" })}</div>
        <div class="span-3">${kpi({ label: "Owed on cards (est.)", value: money0(cf.owedTotal), foot: "charges since each card's last repayment", ic: "cart", tint: "amber" })}</div>
        <div class="span-3">${kpi({ label: "Slow stock (no sales 30d)", value: money0(st.noSalesValue), foot: `${(st.noSales || []).length} SKUs · ${money0(st.stockValue)} total in stock`, ic: "box", tint: "accent" })}</div>
        <div class="span-3">${kpi({ label: "Bought, not live 21d+", value: `${nl.length}`, foot: "orders still before 'Live'", ic: "clock", tint: nl.length ? "amber" : "green" })}</div>

        <div class="card span-12">
          <div class="card-head"><div><div class="card-title">💸 Refund & cancellation chaser</div><div class="card-sub">Charged-but-cancelled orders and units missing at prep. Due after ${ch.days} days, then again ${ch.days} days after each "Chased".</div></div></div>
          ${ch.due.length ? `<div class="list">${ch.due.map((x) => chaseRow(x, true)).join("")}</div>` : `<div class="empty">Nothing due to chase ✓</div>`}
          ${ch.waiting.length ? `<div class="cell-sub" style="margin:12px 0 6px">Waiting (not due yet)</div><div class="list">${ch.waiting.map((x) => chaseRow(x, false)).join("")}</div>` : ""}
        </div>

        ${digestCard(I.digest, false)}

        <div class="card span-6">
          <div class="card-head"><div><div class="card-title">💷 Cash flow (estimate)</div><div class="card-sub">${esc(cf.note || "")}</div></div></div>
          <div class="list">
            ${cards.map(([k, c]) => `<div class="list-item"><span class="kpi-icon tint-amber">${icon("cart")}</span><div class="list-body"><div class="list-title">${esc(k)}</div>
              <div class="list-meta">${c.lastPayment ? `last repayment ${gbp(c.lastPayment.amount, 0)} on ${esc(c.lastPayment.date)}` : "no repayment in export"}${c.avgMonthlyRepayment ? ` · usually ~${gbp(c.avgMonthlyRepayment, 0)}/month` : ""} · export to ${esc(c.statementTo)}</div></div>
              <div class="list-right"><b>${money0(c.owedSinceLastPayment)}</b><div class="cell-sub">owed since</div></div></div>`).join("")}
            <div class="list-item"><span class="kpi-icon tint-green">${icon("pound")}</span><div class="list-body"><div class="list-title">Revolut Business balance</div><div class="list-meta">${cf.revolut ? "as of " + esc(cf.revolut.asOf) : "no Revolut export"}</div></div><div class="list-right"><b>${cf.revolut ? money0(cf.revolut.balance) : "—"}</b></div></div>
            <div class="list-item"><span class="kpi-icon tint-blue">${icon("trend")}</span><div class="list-body"><div class="list-title">Spending per week</div><div class="list-meta">last 4 weeks, transfers excluded</div></div><div class="list-right"><b>${money0(cf.weeklySpend)}</b></div></div>
            <div class="list-item"><span class="kpi-icon tint-accent">${icon("chart")}</span><div class="list-body"><div class="list-title">Amazon sales, last 30 days</div><div class="list-meta">from Invenno (paid out in batches by Amazon)</div></div><div class="list-right"><b>${money0(cf.amazonSales30)}</b></div></div>
          </div>
          <div class="banner ${cf.gap < 0 ? "" : "ok"}" style="margin-top:12px">${icon(cf.gap < 0 ? "alert" : "shield")}<span>Revolut balance minus what's owed on the cards: <b>${money0(cf.gap)}</b>${cf.gap < 0 ? ": you'll need incoming Amazon payouts to clear the cards." : "."}</span></div>
        </div>

        <div class="card span-6">
          <div class="card-head"><div><div class="card-title">⏳ Bought but not live after ${st.limits ? st.limits.notLive : 21} days</div><div class="card-sub">From the Purchases tracker</div></div><a class="link" href="#purchases">Purchases</a></div>
          ${nl.length ? `<div class="list">${nl.slice(0, 12).map((c) => `<div class="list-item"><span class="kpi-icon tint-amber">${icon("clock")}</span><div class="list-body"><div class="list-title">${esc(c.source)} · ${c.qty}× ${esc((c.title || "").slice(0, 60))}</div><div class="list-meta">${esc({ ordered: "Ordered", shipped: "In transit", delivered: "Delivered", atprep: "At prep", prepped: "Prepped" }[c.stage] || c.stage)} · bought ${esc(c.orderedAt.slice(0, 10))}</div></div></div>`).join("")}</div>${nl.length > 12 ? `<div class="cell-sub" style="margin-top:6px">+${nl.length - 12} more on the Purchases page</div>` : ""}` : `<div class="empty">Everything bought 21+ days ago is live ✓</div>`}
        </div>

        <div class="card span-12 flush">
          <div class="card-head" style="padding:16px 18px 0"><div><div class="card-title">🐢 Live but no sales in ${st.limits ? st.limits.noSales : 30} days</div><div class="card-sub">${st.updated ? "Invenno inventory · updated " + esc(st.updated) : st.error ? esc(st.error) : "Loading from Invenno (first run takes a few minutes after a restart)…"} · ${money0(st.noSalesValue)} tied up</div></div></div>
          <div class="table-wrap"><table><thead><tr><th>Product</th><th class="num">In stock</th><th class="num">Age</th><th class="num">Sold 30d</th><th class="num">Cost/unit</th><th class="num">Tied up</th></tr></thead>
            <tbody>${(st.noSales || []).map(stockRow).join("") || `<tr><td colspan="6" class="empty">None ✓</td></tr>`}</tbody></table></div>
        </div>
        <div class="card span-12 flush">
          <div class="card-head" style="padding:16px 18px 0"><div><div class="card-title">📦 Still in stock after ${st.limits ? st.limits.old : 60}+ days</div><div class="card-sub">${money0(st.oldValue)} tied up</div></div></div>
          <div class="table-wrap"><table><thead><tr><th>Product</th><th class="num">In stock</th><th class="num">Age</th><th class="num">Sold 30d</th><th class="num">Cost/unit</th><th class="num">Tied up</th></tr></thead>
            <tbody>${(st.old || []).map(stockRow).join("") || `<tr><td colspan="6" class="empty">None ✓</td></tr>`}</tbody></table></div>
        </div>
      </div>`;
  };
  async function loadInsights(force) {
    try { D.insights = await (await fetch("/api/insights" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    const n = (D.insights.chaser || { due: [] }).due.length;
    const nav = document.querySelector('.nav-item[href="#insights"] .count');
    if (nav) { nav.textContent = n || ""; nav.style.display = n ? "" : "none"; nav.classList.toggle("hot", n > 0); }
    const h = location.hash.slice(1).split("?")[0] || "overview";
    if (h === "insights" || h === "overview") render();
  }
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-chase]");
    if (b) { b.disabled = true; await fetch("/api/insights/chase", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: b.dataset.chase, action: b.dataset.act }) }); loadInsights(); }
    if (e.target.closest("#insRefresh")) { D.insights = { loading: true }; render(); loadInsights(true); }
  });
  setTimeout(loadInsights, 4000);
  setInterval(loadInsights, 15 * 60 * 1000);

  // ---------- Command palette (Ctrl+K) ----------
  function paletteItems() {
    const pages = NAV.filter((n) => n.id).map((n) => ({ group: "Pages", label: n.label, ic: n.icon, go: "#" + n.id }));
    const products = D.fba.topProducts.map((p) => ({ group: "Products", label: p.title, ic: "box", sub: p.asin, go: "#fba" }));
    const leads = D.deals.leads.map((l) => ({ group: "Deal leads", label: l.title, ic: "bolt", sub: `${l.source} · ${gbp(l.profit)}`, go: "#deals" }));
    const jobs = D.jobs.matches.map((j) => ({ group: "Jobs", label: `${j.title} — ${j.company}`, ic: "briefcase", sub: j.rating + (D.jobsLive ? "/10" : "%"), go: "#jobs" }));
    const notes = D.notes.map((n, i) => ({ group: "Memory", label: n.title, ic: "note", sub: n.type, go: "#memory", note: i }));
    return [...pages, ...products, ...leads, ...jobs, ...notes];
  }
  let palSel = 0, palResults = [];
  function renderPalette() {
    const q = $("#paletteInput").value.trim().toLowerCase();
    palResults = paletteItems().filter((it) => !q || (it.label + " " + (it.sub || "")).toLowerCase().includes(q)).slice(0, 40);
    palSel = Math.min(palSel, Math.max(0, palResults.length - 1));
    let last = "";
    const ans = askAnswer($("#paletteInput").value.trim());
    const askHtml = ans ? `<div class="ask-answer"><div class="ask-q"><span class="mini-orb"></span>Answer</div><div class="ask-a">${ans.a}</div>${ans.go ? `<a class="ask-go" href="${ans.go}">Open page ›</a>` : ""}</div>` : "";
    $("#paletteList").innerHTML = askHtml + (palResults.length ? palResults.map((it, i) => {
      const head = it.group !== last ? `<div class="palette-group">${it.group}</div>` : "";
      last = it.group;
      return `${head}<div class="palette-item ${i === palSel ? "sel" : ""}" data-pi="${i}">${icon(it.ic)}<span>${esc(it.label)}</span>${it.sub ? `<span class="cell-sub">${esc(it.sub)}</span>` : ""}</div>`;
    }).join("") : ans ? "" : `<div class="empty">No results</div>`);
    $("#paletteList .sel")?.scrollIntoView({ block: "nearest" });
  }
  function openPalette() {
    $("#palette").classList.add("open");
    $("#paletteInput").value = "";
    palSel = 0;
    renderPalette();
    setTimeout(() => $("#paletteInput").focus(), 0);
  }
  const closePalette = () => $("#palette").classList.remove("open");
  document.addEventListener("click", (e) => { if (e.target.closest(".ask-go")) closePalette(); });
  function choose(it) {
    if (!it) return;
    closePalette();
    if (it.note !== undefined) activeNote = it.note;
    if (location.hash === it.go) route(); else location.hash = it.go;
  }
  $("#paletteInput").addEventListener("input", () => { palSel = 0; renderPalette(); });
  $("#paletteInput").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); palSel = Math.min(palSel + 1, palResults.length - 1); renderPalette(); }
    if (e.key === "ArrowUp") { e.preventDefault(); palSel = Math.max(palSel - 1, 0); renderPalette(); }
    if (e.key === "Enter") choose(palResults[palSel]);
  });
  $("#paletteList").addEventListener("click", (e) => { const el = e.target.closest("[data-pi]"); if (el) choose(palResults[+el.dataset.pi]); });
  $("#palette").addEventListener("click", (e) => { if (e.target.id === "palette") closePalette(); });
  $("#search").addEventListener("focus", (e) => { e.target.blur(); openPalette(); });
  document.addEventListener("click", (e) => { if (e.target.closest("#openPalette")) openPalette(); });

  // ---------- Misc ----------
  $("#menuBtn").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); }
    if (e.key === "Escape") closePalette();
  });
  const tick = () => {
    $("#clock").textContent = new Date().toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };
  tick(); setInterval(tick, 15000);

  // ---------- Live ticker ----------
  function buildTicker() {
    const items = [
      ...D.deals.monitors.map((m) => `<span>${m.name.toUpperCase()} <b class="${m.status === "err" ? "down" : ""}">${{ ok: "ONLINE", warn: "DELAYED", idle: "IDLE", err: "STOPPED" }[m.status]}</b> · ${m.leadsToday} today</span>`),
      ...D.deals.leads.filter((l) => l.source !== "HUKD" && l.profit != null).slice(0, 4).map((l) => `<span>${l.source.toUpperCase()} › ${esc(l.title.slice(0, 45))} <span class="up">+${gbp(l.profit)}</span></span>`),
      `<span>ISA <b>${gbp(D.isa.value)}</b> <span class="${D.isa.dayChangePct >= 0 ? "up" : "down"}">${D.isa.dayChangePct >= 0 ? "▲" : "▼"}${Math.abs(D.isa.dayChangePct).toFixed(2)}%</span></span>`,
      `<span>SALES TODAY <b>${gbp(D.fba.today.profit)}</b> profit · ${D.fba.today.units ?? "—"} units</span>`,
      ...((D.otp && D.otp.codes) || []).filter((c) => c.today).map((c) => `<span>${c.dest === "Prep" ? "PREP" : c.dest === "Me" ? "HOME" : "CHECK"} CODE › <b>${esc(c.code)}</b> ${esc(c.carrier)}${c.window ? " " + esc(c.window) : ""}</span>`),
      ...(D.important && D.important.items ? impItems().filter((x) => x.priority === 1).slice(0, 3).map((x) => `<span>EMAIL › ${esc(x.subject.slice(0, 50))} <b class="down">${esc(x.reason.toUpperCase())}</b></span>`) : []),
      ...(typeof actionItems === "function" ? actionItems().slice(0, 3).map((a) => `<span>CLAIMS › ${esc(a.title.slice(0, 40))} <b class="${a.days <= 7 ? "down" : ""}">${a.days != null ? a.days + "D LEFT" : ""}</b></span>`) : []),
    ].join("");
    $("#tickerTrack").innerHTML = items + items; // doubled for a seamless loop
  }
  buildTicker();

  // ---------- Boot sequence (once per browser session) ----------
  function boot() {
    let seen = false;
    try { seen = sessionStorage.getItem("cc-booted") === "1"; sessionStorage.setItem("cc-booted", "1"); } catch {}
    const el = $("#boot");
    if (seen) { el.remove(); return; }
    const lines = ["Connecting to sales data", "Syncing deal monitors", "Loading job pipeline", "Reading portfolio", "Indexing memory"];
    $("#bootLines").innerHTML = lines.map((l, i) => `<div class="boot-line" style="animation-delay:${i * 170}ms">› ${l} <span class="ok">[ OK ]</span></div>`).join("")
      + `<div class="boot-line cursor" style="animation-delay:${lines.length * 170}ms">› Command Centre online</div>`;
    setTimeout(() => { el.classList.add("done"); setTimeout(() => el.remove(), 600); }, lines.length * 170 + 450);
  }
  boot();

  // ---------- Live sales data (Invenno) ----------
  async function loadFba(force) {
    let d;
    try { d = await (await fetch("/api/fba" + (force ? "?refresh=1" : ""))).json(); } catch { return; }
    D.fbaStatus = d;
    if (d.sales30) {
      D.fba = {
        today: { sales: d.today.sales, profit: d.today.profit, units: d.today.units, margin: d.today.margin != null ? +d.today.margin.toFixed(1) : "—" },
        yesterday: d.yesterday,
        month: { ...d.month, target: D.fba.month.target },
        d30: d.d30,
        deltas: { profit: d.month.profitChange ?? 0, sales: d.month.salesChange ?? 0, units: 0, margin: 0 },
        profit30: d.profit30, sales30: d.sales30, labels: d.labels,
        topProducts: d.topProducts,
        alerts: d.alerts,
        inventory: d.inventory,
      };
      D.fbaLive = true;
      $("#sampleTag").textContent = "Memory page: sample data";
      buildTicker();
    }
    const h = location.hash.slice(1) || "overview";
    if (h === "fba" || h === "overview") render();
    if (d.loading) setTimeout(loadFba, 5000);
  }
  D.fbaStatus = { loading: true };
  loadFba();
  loadRange();
  setInterval(loadFba, 5 * 60 * 1000);
  document.addEventListener("click", (e) => {
    if (e.target.closest("#fbaRefresh")) { D.fbaStatus = { loading: true }; render(); loadFba(true).then(() => setTimeout(loadFba, 8000)); }
  });

  route();
})();
