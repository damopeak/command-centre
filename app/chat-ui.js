// Claude chat panel: Ask (any question + live dashboard data + web) and Edit dashboard (changes the front-end, with undo).
(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = {
    get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  let msgs = store.get("cc-chat", []);
  let mode = store.get("cc-chat-mode", "ask");
  let busy = false;

  // Minimal, safe markdown: escape first, then bold / code / links / lists
  function md(text) {
    const lines = esc(text).split(/\r?\n/);
    let html = "", list = null;
    const inline = (s) => s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/(^|\s)(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
    for (const raw of lines) {
      const ul = /^\s*[-*•]\s+(.*)/.exec(raw), ol = /^\s*\d+[.)]\s+(.*)/.exec(raw);
      const kind = ul ? "ul" : ol ? "ol" : null;
      if (kind !== list) { if (list) html += `</${list}>`; if (kind) html += `<${kind}>`; list = kind; }
      if (kind) html += `<li>${inline((ul || ol)[1])}</li>`;
      else if (/^#{1,4}\s/.test(raw)) html += `<div class="cm-h">${inline(raw.replace(/^#+\s/, ""))}</div>`;
      else if (raw.trim()) html += `<p>${inline(raw)}</p>`;
    }
    if (list) html += `</${list}>`;
    return html;
  }

  const root = document.createElement("div");
  root.innerHTML = `
    <button class="cm-fab" id="cmFab" aria-label="Chat with Claude"><span class="cm-orb"><i></i><i></i></span></button>
    <section class="cm-panel" id="cmPanel" aria-label="Claude chat">
      <header class="cm-head">
        <span class="cm-orb sm"><i></i><i></i></span>
        <div class="cm-title"><b>Claude</b><span id="cmSub">Ask me anything</span></div>
        <div class="cm-seg" role="tablist">
          <button data-mode="ask">Ask</button><button data-mode="edit">Edit dashboard</button>
        </div>
        <button class="cm-x" id="cmClear" title="Clear chat">⟲</button>
        <button class="cm-x" id="cmClose" title="Close">✕</button>
      </header>
      <div class="cm-body" id="cmBody"></div>
      <form class="cm-input" id="cmForm">
        <textarea id="cmText" rows="1" placeholder="Ask anything…"></textarea>
        <button type="submit" class="cm-send" aria-label="Send">➤</button>
      </form>
    </section>`;
  document.body.appendChild(root);

  const SUGGEST = {
    ask: ["What needs my attention today?", "Best Discord leads right now?", "Summarise my week", "What's on tomorrow?"],
    edit: ["Make the KPI numbers bigger", "Add a 'Units today' card to the overview", "Use rounder corners on the cards"],
  };
  function render() {
    document.querySelectorAll(".cm-seg button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
    $("#cmSub").textContent = mode === "ask" ? "Ask me anything · sees your dashboard + the web" : "Describe a change · backed up with undo";
    $("#cmText").placeholder = mode === "ask" ? "Ask anything…" : "e.g. make the profit number green";
    const body = $("#cmBody");
    body.innerHTML = (msgs.length ? "" : `<div class="cm-empty"><div class="cm-hello">${mode === "ask" ? "Hello, what can I help with?" : "What should I change on the dashboard?"}</div>
        ${mode === "edit" ? `<div class="cm-note">I can change the design and layout. Each change is backed up, and you can undo it. Changes to the data behind the dashboard still go through the main Claude chat.</div>` : ""}
        <div class="cm-chips">${SUGGEST[mode].map((s) => `<button class="cm-chip">${esc(s)}</button>`).join("")}</div></div>`)
      + msgs.map((m, i) => `<div class="cm-msg ${m.role}${m.error ? " err" : ""}">
          ${m.role === "user" ? `<div class="cm-bubble">${esc(m.text)}</div>` : `<div class="cm-bubble">${md(m.text)}
            ${m.backup ? `<div class="cm-actions"><button class="cm-btn" data-reload>↻ Reload to see it</button><button class="cm-btn ghost" data-undo="${esc(m.backup)}" ${m.undone ? "disabled" : ""}>${m.undone ? "Undone ✓" : "↶ Undo"}</button></div>` : ""}</div>`}
          <span class="cm-meta">${m.mode === "edit" ? "edit · " : ""}${esc(m.at || "")}</span></div>`).join("")
      + (busy ? `<div class="cm-msg assistant"><div class="cm-bubble cm-typing"><span></span><span></span><span></span><em>${mode === "edit" ? "Editing the dashboard… (up to a few minutes)" : "Thinking…"}</em></div></div>` : "");
    body.scrollTop = body.scrollHeight;
  }

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    const at = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    msgs.push({ role: "user", text, at, mode });
    busy = true; render(); store.set("cc-chat", msgs.slice(-40));
    const sendMode = mode;
    try {
      const r = await (await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: sendMode, messages: msgs.filter((m) => !m.error).map((m) => ({ role: m.role, text: m.text })) }) })).json();
      const at2 = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
      if (r.ok) msgs.push({ role: "assistant", text: r.text + (sendMode === "edit" && r.changed && r.changed.length ? `\n\nChanged: ${r.changed.join(", ")}` : sendMode === "edit" ? "\n\n(No files changed.)" : ""), at: at2, mode: sendMode, backup: r.backup || null });
      else msgs.push({ role: "assistant", text: r.error || "Something went wrong.", at: at2, error: true });
    } catch (e) {
      msgs.push({ role: "assistant", text: "Couldn't reach the dashboard server.", error: true });
    }
    busy = false; store.set("cc-chat", msgs.slice(-40)); render();
  }

  const open = (v) => { $("#cmPanel").classList.toggle("open", v); $("#cmFab").classList.toggle("hide", v); if (v) { render(); setTimeout(() => $("#cmText").focus(), 200); } store.set("cc-chat-open", v); };
  $("#cmFab").onclick = () => open(true);
  $("#cmClose").onclick = () => open(false);
  $("#cmClear").onclick = () => { if (busy) return; msgs = []; store.set("cc-chat", msgs); render(); };
  document.querySelectorAll(".cm-seg button").forEach((b) => (b.onclick = () => { mode = b.dataset.mode; store.set("cc-chat-mode", mode); render(); }));
  $("#cmForm").onsubmit = (e) => { e.preventDefault(); const t = $("#cmText"); send(t.value); t.value = ""; t.style.height = ""; };
  $("#cmText").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#cmForm").requestSubmit(); } });
  $("#cmText").addEventListener("input", (e) => { e.target.style.height = ""; e.target.style.height = Math.min(140, e.target.scrollHeight) + "px"; });
  $("#cmBody").addEventListener("click", async (e) => {
    const chip = e.target.closest(".cm-chip"); if (chip) return send(chip.textContent);
    if (e.target.closest("[data-reload]")) return location.reload();
    const u = e.target.closest("[data-undo]");
    if (u && !u.disabled) {
      const r = await (await fetch("/api/chat/undo", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ backup: u.dataset.undo }) })).json();
      const m = msgs.find((x) => x.backup === u.dataset.undo); if (m && r.ok) m.undone = true;
      msgs.push({ role: "assistant", text: r.ok ? "Undone. Reload the page to see the previous version." : r.error, error: !r.ok });
      store.set("cc-chat", msgs.slice(-40)); render();
    }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#cmPanel").classList.contains("open")) open(false); if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "j") { e.preventDefault(); open(!$("#cmPanel").classList.contains("open")); } });
  if (store.get("cc-chat-open", false)) open(true);
})();
