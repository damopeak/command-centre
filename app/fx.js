// Visual effects: neural-net background, cursor glow on cards, title decode, typed AI brief.
(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Neural network background ----------
  const cv = document.createElement("canvas");
  cv.id = "neural";
  document.body.prepend(cv);
  const ctx = cv.getContext("2d");
  let W = 0, H = 0, nodes = [], mouse = { x: -9999, y: -9999 };
  const DPR = Math.min(devicePixelRatio || 1, 1.5);

  function size() {
    W = innerWidth; H = innerHeight;
    cv.width = W * DPR; cv.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    const n = Math.round(Math.min(80, (W * H) / 22000));
    nodes = Array.from({ length: n }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - .5) * .18, vy: (Math.random() - .5) * .18,
      r: Math.random() * 1.4 + .6, p: Math.random() * Math.PI * 2,
    }));
  }
  size();
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(size, 150); });
  addEventListener("pointermove", (e) => { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
  document.addEventListener("pointerleave", () => { mouse.x = mouse.y = -9999; });

  // Signal pulses travelling along links
  const pulses = [];
  // Theme colours from CSS variables (re-read when the theme changes)
  let C = {};
  function readColours() {
    const cs = getComputedStyle(document.documentElement);
    const g = (n) => cs.getPropertyValue(n).trim().replace(/\s+/g, "");
    C = { a: g("--a-rgb") || "139,123,255", b: g("--b-rgb") || "79,209,255", p: g("--g-rgb") || "79,240,180" };
  }
  readColours();
  const LINK = 150;
  function frame(t) {
    ctx.clearRect(0, 0, W, H);
    for (const a of nodes) {
      if (!reduce) { a.x += a.vx; a.y += a.vy; }
      if (a.x < -20) a.x = W + 20; else if (a.x > W + 20) a.x = -20;
      if (a.y < -20) a.y = H + 20; else if (a.y > H + 20) a.y = -20;
    }
    ctx.lineWidth = 1;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 > LINK * LINK) continue;
        const k = 1 - Math.sqrt(d2) / LINK;
        const mx = (a.x + b.x) / 2 - mouse.x, my = (a.y + b.y) / 2 - mouse.y;
        const near = Math.max(0, 1 - Math.sqrt(mx * mx + my * my) / 220);
        ctx.strokeStyle = `rgba(${near > 0 ? C.b : C.a},${(k * .13 + near * k * .35).toFixed(3)})`;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        if (!reduce && pulses.length < 6 && Math.random() < .00035) pulses.push({ a, b, s: 0 });
      }
    }
    for (const a of nodes) {
      const glow = .35 + Math.sin(t / 900 + a.p) * .25;
      ctx.fillStyle = `rgba(${C.a},${(glow + .15).toFixed(3)})`;
      ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 6.283); ctx.fill();
    }
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i]; p.s += .012;
      if (p.s >= 1) { pulses.splice(i, 1); continue; }
      const x = p.a.x + (p.b.x - p.a.x) * p.s, y = p.a.y + (p.b.y - p.a.y) * p.s;
      const g = ctx.createRadialGradient(x, y, 0, x, y, 7);
      g.addColorStop(0, `rgba(${C.p},.9)`); g.addColorStop(1, `rgba(${C.p},0)`);
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 7, 0, 6.283); ctx.fill();
    }
  }
  let last = 0;
  function loop(t) {
    requestAnimationFrame(loop);
    if (document.hidden || t - last < 33) return; // ~30fps is plenty for a backdrop
    last = t; frame(t);
  }
  if (reduce) frame(0); else requestAnimationFrame(loop);

  // ---------- Cursor glow on cards ----------
  // ---------- Cursor glow + 3D tilt on cards ----------
  let tilted = null;
  const untilt = (c) => {
    c.classList.remove("tilting"); c.classList.add("tilt-reset");
    c.style.removeProperty("--rx"); c.style.removeProperty("--ry");
    setTimeout(() => c.classList.remove("tilt-reset"), 600);
  };
  document.addEventListener("pointermove", (e) => {
    const c = e.target.closest && e.target.closest(".card");
    if (tilted && tilted !== c) { untilt(tilted); tilted = null; }
    if (!c) return;
    const r = c.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    c.style.setProperty("--mx", `${x}px`);
    c.style.setProperty("--my", `${y}px`);
    // Tilt only small/medium cards; wide tables would feel seasick
    if (reduce || e.pointerType !== "mouse" || r.width > 640 || r.height > 520) return;
    const max = 5;
    c.style.setProperty("--ry", `${((x / r.width) - .5) * max * 2}deg`);
    c.style.setProperty("--rx", `${(.5 - (y / r.height)) * max * 2}deg`);
    if (!c.classList.contains("tilting")) { c.classList.remove("tilt-reset"); c.classList.add("tilting"); }
    tilted = c;
  }, { passive: true });
  document.addEventListener("pointerleave", () => { if (tilted) { untilt(tilted); tilted = null; } });

  // ---------- Title decode ----------
  const GLYPHS = "01<>/\\{}[]#$%&*+=?ABCDEFGHJKLMNPQRSTUVWXYZ";
  function decode(el) {
    if (reduce || !el || el.dataset.decoded) return;
    el.dataset.decoded = "1";
    const final = el.textContent, len = final.length, t0 = performance.now(), dur = 520;
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur), done = Math.floor(k * len);
      let out = final.slice(0, done);
      for (let i = done; i < len; i++) out += final[i] === " " ? " " : GLYPHS[(Math.random() * GLYPHS.length) | 0];
      el.textContent = out;
      if (k < 1) requestAnimationFrame(step); else el.textContent = final;
    };
    requestAnimationFrame(step);
  }

  // ---------- Typed AI brief ----------
  let typeToken = 0;
  function typeBrief(root) {
    const lines = [...root.querySelectorAll(".brief-line")];
    if (!lines.length) return;
    if (reduce) { lines.forEach((l) => l.classList.add("shown")); return; }
    const my = ++typeToken;
    const texts = lines.map((l) => l.querySelector(".brief-text").innerHTML);
    lines.forEach((l) => { l.querySelector(".brief-text").innerHTML = ""; });
    let i = 0;
    const next = () => {
      if (my !== typeToken || i >= lines.length) return;
      const line = lines[i], tgt = line.querySelector(".brief-text"), html = texts[i];
      line.classList.add("shown", "typing");
      // Type the plain text, then swap in the formatted HTML
      const tmp = document.createElement("div"); tmp.innerHTML = html;
      const plain = tmp.textContent; let c = 0;
      const tick = () => {
        if (my !== typeToken) return;
        c = Math.min(plain.length, c + 2);
        tgt.textContent = plain.slice(0, c);
        if (c < plain.length) setTimeout(tick, 12);
        else { tgt.innerHTML = html; line.classList.remove("typing"); i++; setTimeout(next, 90); }
      };
      tick();
    };
    // Wait for the boot screen to clear so the typing is actually seen
    const start = () => { const bt = document.getElementById("boot"); if (bt && !bt.classList.contains("done")) return setTimeout(start, 120); setTimeout(next, 250); };
    start();
  }

  const THEMES = [
    { id: "nebula", name: "Nebula", sw: "linear-gradient(90deg,#8b7bff,#4fd1ff)" },
    { id: "matrix", name: "Matrix", sw: "linear-gradient(90deg,#00e676,#8cffbe)" },
    { id: "cyberpunk", name: "Cyberpunk", sw: "linear-gradient(90deg,#ff2e97,#ffdd00)" },
    { id: "ice", name: "Ice", sw: "linear-gradient(90deg,#6eaaff,#aaebff)" },
    { id: "ember", name: "Ember", sw: "linear-gradient(90deg,#ff7043,#ffc457)" },
  ];
  function setTheme(id, save) {
    if (id === "nebula") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", id);
    if (save) { try { localStorage.setItem("cc-theme", id); } catch {} }
    readColours();
    document.querySelectorAll(".theme-opt").forEach((b) => b.classList.toggle("on", b.dataset.theme === id));
    window.dispatchEvent(new Event("themechange"));
  }
  try { setTheme(localStorage.getItem("cc-theme") || "nebula"); } catch { setTheme("nebula"); }

  window.FX = {
    themes: THEMES,
    setTheme,
    // Called after each render; quiet = data refresh of the same page (no entrance effects)
    after(view, quiet) {
      if (quiet) {
        typeToken++;
        view.querySelectorAll(".brief-line").forEach((l) => l.classList.add("shown"));
        return;
      }
      decode(view.querySelector(".page-head h1"));
      typeBrief(view);
    },
  };
})();
