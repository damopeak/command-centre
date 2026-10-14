// Purchases Tracker sync. Paste this into the sheet: Extensions > Apps Script, replace everything, Save.
// Then Run > setup (styles the sheet now) and Deploy > New deployment > Web app (Execute as: Me, Access: Anyone).
// The Command Centre posts every order here every 20 minutes. Rows are added or updated, never deleted.
// Oldest orders at the top; new ones appear as you scroll down. Your columns (Paid with, Action, Checked) are never overwritten.
const TOKEN = "CHANGE_ME";   // must match SHEET_WEBHOOK_TOKEN in .env
// Columns. The Command Centre fills the "managed" ones; "yours" are never overwritten.
const HEADERS = ["Ordered", "Store", "Order number", "Item", "Qty", "Total", "Currency", "Deliver to", "Stage",
  "Shipped", "Delivered", "Received at prep", "Prepped", "Sent to Amazon", "Live", "Problems",
  "Notes", "Payment", "Paid with", "Action", "Checked", "Expected", "Last updated", "Key"];
const YOURS = ["Paid with", "Action", "Checked"];          // Notes is two-way synced (see below)
const HEADER_ROW = 2, FIRST = 3;                            // row 1 = totals bar
const COL = {}; HEADERS.forEach((h, i) => COL[h] = i + 1);
const NCOL = HEADERS.length;

const PAID = ["Amex", "Capital on Tap", "Revolut", "Other"];
const ACTIONS = ["To chase", "Refund pending", "Return started", "Claim filed", "Resolved"];
const STAGE_COLOURS = {   // background, text
  "Ordered": ["#e3e7f1", "#2f3b57"], "In transit": ["#e6e0fb", "#47318f"], "Delivered": ["#dbe9fb", "#1f4f8f"],
  "At prep": ["#ffecc2", "#7a4b00"], "Prepped": ["#ffd9b8", "#8a3d00"], "Sent to Amazon": ["#d6f1fb", "#0d5c78"],
  "Live": ["#cff3e2", "#0b5d3b"], "Cancelled": ["#fbd5da", "#8f1d2c"],
};
const ACTION_COLOURS = { "To chase": ["#fbd5da", "#8f1d2c"], "Refund pending": ["#ffecc2", "#7a4b00"],
  "Return started": ["#e6e0fb", "#47318f"], "Claim filed": ["#dbe9fb", "#1f4f8f"], "Resolved": ["#cff3e2", "#0b5d3b"] };

// Run once from the editor (Run > setup) to style the empty sheet straight away
function setup() { const sh = sheet_(); format_(sh); }

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName("Orders") || ss.getSheets()[0];
  if (sh.getName() !== "Orders") sh.setName("Orders");
  // Older layout had headers in row 1: move them down to make room for the totals bar
  if (sh.getRange(1, 1).getValue() === "Ordered") sh.insertRowBefore(1);
  if (sh.getMaxColumns() < NCOL) sh.insertColumnsAfter(sh.getMaxColumns(), NCOL - sh.getMaxColumns());
  return sh;
}

// Remember when you type a note in the sheet, so the newer side wins when syncing with the dashboard
function onEdit(e) {
  const sh = e.range.getSheet();
  if (sh.getName() !== "Orders" || e.range.getRow() < FIRST) return;
  if (COL.Notes < e.range.getColumn() || COL.Notes > e.range.getLastColumn()) return;
  const props = PropertiesService.getDocumentProperties();
  const keys = sh.getRange(e.range.getRow(), COL.Key, e.range.getNumRows(), 1).getValues();
  const now = new Date().toISOString();
  keys.forEach(k => { if (k[0]) props.setProperty("n:" + k[0], now); });
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents || "{}");
  if (body.token !== TOKEN) return out_({ ok: false, error: "bad token" });
  if (body.action === "calendar") return out_(calendar_(body.events || [], body.remove || []));
  const lock = LockService.getDocumentLock(); lock.waitLock(30000);
  try {
    const sh = sheet_();
    const last = sh.getLastRow();
    // Read rows by the header row as it is now, so adding or moving columns never scrambles data
    const width = Math.max(sh.getLastColumn(), NCOL);
    const oldHead = sh.getRange(HEADER_ROW, 1, 1, width).getValues()[0].map(String);
    const raw = last >= FIRST ? sh.getRange(FIRST, 1, last - FIRST + 1, width).getValues() : [];
    const existing = raw.map(r => HEADERS.map(h => { const i = oldHead.indexOf(h); return i >= 0 ? r[i] : (h === "Checked" ? false : ""); }))
                        .filter(r => r[COL.Key - 1]);
    sh.getRange(HEADER_ROW, 1, 1, NCOL).setValues([HEADERS]);
    if (width > NCOL) sh.getRange(HEADER_ROW, NCOL + 1, 1, width - NCOL).clearContent();
    const index = {}; existing.forEach((r, i) => { if (r[COL.Key - 1]) index[r[COL.Key - 1]] = i; });
    const props = PropertiesService.getDocumentProperties();
    const notesBack = {}, appends = [];
    let updated = 0;
    (body.rows || []).forEach(r => {
      const i = index[r.Key];
      const cur = i === undefined ? null : existing[i];
      const vals = HEADERS.map((h, c) => {
        if (YOURS.includes(h)) return cur ? cur[c] : (h === "Checked" ? false : "");
        const v = r[h];
        return v === undefined || v === null ? "" : v;
      });
      if (cur) {
        const sheetNote = String(cur[COL.Notes - 1] || ""), sheetAt = props.getProperty("n:" + r.Key) || "";
        if (sheetNote !== String(r.Notes || "") && sheetAt && (!r.NotesAt || new Date(sheetAt) > new Date(r.NotesAt))) {
          vals[COL.Notes - 1] = sheetNote;
          notesBack[r.Key] = { text: sheetNote, at: sheetAt };
        }
        if (cur.map(String).join("|") !== vals.map(String).join("|")) { existing[i] = vals; updated++; }
      } else appends.push(vals);
    });
    const all = existing.concat(appends);
    if (all.length) {
      const need = FIRST + all.length + 200;
      if (sh.getMaxRows() < need) sh.insertRowsAfter(sh.getMaxRows(), need - sh.getMaxRows());
      const when = (v) => v instanceof Date ? v.getTime() : (Date.parse(String(v).replace(" ", "T")) || 0);
      all.sort((a, b) => when(a[0]) - when(b[0]));   // oldest at the top
      // clear old dropdowns/tick boxes first (columns can move between versions); format_ puts them back in the right place
      sh.getRange(FIRST, 1, sh.getMaxRows() - FIRST + 1, Math.max(sh.getMaxColumns(), NCOL)).clearDataValidations();
      sh.getRange(FIRST, 1, sh.getMaxRows() - FIRST + 1, NCOL).clearContent();   // pack orders from row 3, no gaps
      sh.getRange(FIRST, 1, all.length, NCOL).setValues(all);
    }
    format_(sh);
    const tx = body.transactions && body.transactions.length ? transactions_(body.transactions) : { answers: {} };
    return out_({ ok: true, v: 5, added: appends.length, updated: updated, total: all.length, notes: notesBack, answers: tx.answers, txTotal: tx.total });
  } finally { lock.releaseLock(); }
}

function letter_(c) { let s = ""; while (c > 0) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26); } return s; }
function col_(name) { const L = letter_(COL[name]); return `${L}${FIRST}:${L}`; }

function format_(sh) {
  const rows = Math.max(sh.getMaxRows() - FIRST + 1, 1);
  const body = sh.getRange(FIRST, 1, rows, NCOL);

  // Whole sheet
  sh.getRange(1, 1, sh.getMaxRows(), NCOL).setFontFamily("Arial").setFontSize(10).setVerticalAlignment("middle");
  sh.setFrozenRows(HEADER_ROW); sh.setFrozenColumns(0);

  // Totals bar (row 1): formulas over open-ended ranges so new orders are counted
  const T = [
    ["Orders", `=COUNTA(${col_("Key")})`, "0"],
    ["Spent £", `=SUMIFS(${col_("Total")},${col_("Currency")},"£",${col_("Stage")},"<>Cancelled")`, "£#,##0"],
    ["Spent €", `=SUMIFS(${col_("Total")},${col_("Currency")},"€",${col_("Stage")},"<>Cancelled")`, "€#,##0"],
    ["Units", `=SUMIFS(${col_("Qty")},${col_("Stage")},"<>Cancelled")`, "#,##0"],
    ["In transit", `=COUNTIF(${col_("Stage")},"In transit")+COUNTIF(${col_("Stage")},"Ordered")`, "0"],
    ["At prep", `=COUNTIF(${col_("Stage")},"At prep")+COUNTIF(${col_("Stage")},"Prepped")`, "0"],
    ["Live", `=COUNTIF(${col_("Stage")},"Live")+COUNTIF(${col_("Stage")},"Sent to Amazon")`, "0"],
    ["Problems", `=COUNTIF(${col_("Problems")},"?*")`, "0"],
    ["To chase", `=COUNTIF(${col_("Action")},"To chase")`, "0"],
    ["Unchecked", `=COUNTIFS(${col_("Checked")},FALSE,${col_("Key")},"<>")`, "0"],
  ];
  const bar = sh.getRange(1, 1, 1, NCOL);
  bar.clearContent().setBackground("#11131c").setFontColor("#ffffff");
  T.forEach((t, i) => {
    const c = i * 2 + 1;
    sh.getRange(1, c).setValue(t[0]).setFontColor("#a4a9bd").setFontSize(9).setHorizontalAlignment("right");
    sh.getRange(1, c + 1).setFormula(t[1]).setNumberFormat(t[2]).setFontWeight("bold").setFontSize(12).setFontColor("#ffffff").setHorizontalAlignment("left");
  });
  sh.getRange(1, T.findIndex(t => t[0] === "Problems") * 2 + 2).setFontColor("#ff6b81");
  sh.setRowHeight(1, 34);

  // Header row
  sh.getRange(HEADER_ROW, 1, 1, NCOL).setBackground("#2b2f45").setFontColor("#ffffff").setFontWeight("bold").setWrap(true);
  YOURS.concat(["Notes"]).forEach(h => sh.getRange(HEADER_ROW, COL[h]).setBackground("#5b4bd6"));
  sh.getRange(HEADER_ROW, COL.Notes).setNote("Yours: type notes here. They sync with the dashboard; whichever you edited last wins.");
  sh.getRange(HEADER_ROW, COL["Paid with"]).setNote("Yours: the Command Centre never overwrites this column.");
  sh.setRowHeight(HEADER_ROW, 30);

  // Banded rows over the whole column range, so new rows are banded too
  sh.getBandings().forEach(b => b.remove());
  body.applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);

  // Number / text formats
  sh.getRange(FIRST, COL.Total, rows, 1).setNumberFormat("#,##0.00");
  sh.getRange(FIRST, COL.Qty, rows, 1).setHorizontalAlignment("center").setFontWeight("bold");
  ["Received at prep", "Prepped", "Sent to Amazon", "Live", "Checked"].forEach(h => sh.getRange(FIRST, COL[h], rows, 1).setHorizontalAlignment("center"));
  sh.getRange(FIRST, COL.Stage, rows, 1).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(FIRST, COL["Deliver to"], rows, 1).setFontWeight("bold");
  sh.getRange(FIRST, COL.Notes, rows, 1).setWrap(true);
  sh.getRange(FIRST, COL.Key, rows, 1).setFontColor("#9aa0b4").setFontSize(8);

  // Your columns: dropdowns + tick box
  sh.getRange(FIRST, COL["Paid with"], rows, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(PAID, true).setAllowInvalid(false).build());
  sh.getRange(FIRST, COL.Action, rows, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(ACTIONS, true).setAllowInvalid(false).build());
  sh.getRange(FIRST, COL.Checked, rows, 1).insertCheckboxes();

  // Colours (conditional formats, so they follow the values)
  const rng = (h) => sh.getRange(FIRST, COL[h], rows, 1);
  const rules = [];
  Object.entries(STAGE_COLOURS).forEach(([v, [bg, fg]]) => rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(v).setBackground(bg).setFontColor(fg).setRanges([rng("Stage")]).build()));
  Object.entries(ACTION_COLOURS).forEach(([v, [bg, fg]]) => rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(v).setBackground(bg).setFontColor(fg).setRanges([rng("Action")]).build()));
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextStartsWith("Prep").setBackground("#ffe7b3").setFontColor("#7a4b00").setRanges([rng("Deliver to")]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextStartsWith("Home").setBackground("#c9f2df").setFontColor("#0b5d3b").setRanges([rng("Deliver to")]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("Unknown").setFontColor("#9aa0b4").setRanges([rng("Deliver to")]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied(`=LEN($${letter_(COL.Problems)}${FIRST})>0`).setBackground("#fbd5da").setFontColor("#8f1d2c").setRanges([rng("Problems")]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setFontColor("#0b5d3b").setBold(true).setRanges([rng("Live")]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied(`=$${letter_(COL.Checked)}${FIRST}=TRUE`).setFontColor("#9aa0b4").setRanges([sh.getRange(FIRST, 1, rows, COL.Problems)]).build());
  sh.setConditionalFormatRules(rules);

  // Filters on every column (kept when the range grows)
  const want = sh.getRange(HEADER_ROW, 1, sh.getMaxRows() - HEADER_ROW + 1, NCOL);
  const f = sh.getFilter();
  if (!f) want.createFilter();
  else if (f.getRange().getNumRows() < want.getNumRows() || f.getRange().getRow() !== HEADER_ROW) {
    const saved = []; for (let c = 1; c <= NCOL; c++) { const cr = f.getColumnFilterCriteria(c); if (cr) saved.push([c, cr.copy().build()]); }
    f.remove(); const nf = want.createFilter(); saved.forEach(([c, cr]) => nf.setColumnFilterCriteria(c, cr));
  }

  // Widths
  const W = { "Ordered": 125, "Store": 95, "Order number": 150, "Item": 340, "Qty": 45, "Total": 80, "Currency": 60, "Deliver to": 130,
    "Stage": 115, "Shipped": 120, "Delivered": 120, "Received at prep": 75, "Prepped": 65, "Sent to Amazon": 75, "Live": 50,
    "Problems": 260, "Notes": 260, "Payment": 230, "Paid with": 115, "Action": 125, "Checked": 65, "Expected": 110, "Last updated": 120, "Key": 70 };
  Object.entries(W).forEach(([h, w]) => sh.setColumnWidth(COL[h], w));
}

// ---------- Transactions tab: every card/bank payment, categorised. "Your category" teaches the Command Centre ----------
const TX = ["Date", "Card / account", "Merchant", "Description", "Amount", "Original", "Category", "How", "Matched order", "Question", "Your category", "Note", "Key"];
const TX_YOURS = ["Your category", "Note"];
const TXC = {}; TX.forEach((h, i) => TXC[h] = i + 1);
const CATS = ["Stock", "Prep fees", "Shipping & postage", "Amazon fees", "Amazon payouts", "Refunds", "Software & subscriptions",
  "Phone & internet", "Accountant", "Bank fees", "Fuel", "Train", "Parking", "Meals", "Transfers", "Other / not sure"];

function transactions_(rows) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName("Transactions") || ss.insertSheet("Transactions");
  if (sh.getMaxColumns() < TX.length) sh.insertColumnsAfter(sh.getMaxColumns(), TX.length - sh.getMaxColumns());
  const last = sh.getLastRow(), width = Math.max(sh.getLastColumn(), TX.length);
  const head = last ? sh.getRange(1, 1, 1, width).getValues()[0].map(String) : [];
  const existing = last > 1 ? sh.getRange(2, 1, last - 1, width).getValues().map(r => TX.map(h => { const i = head.indexOf(h); return i >= 0 ? r[i] : ""; })).filter(r => r[TXC.Key - 1]) : [];
  const index = {}; existing.forEach((r, i) => index[r[TXC.Key - 1]] = i);
  const answers = {};
  rows.forEach(r => {
    const i = index[r.Key], cur = i === undefined ? null : existing[i];
    const vals = TX.map(h => TX_YOURS.includes(h) ? (cur ? cur[TXC[h] - 1] : "") : (r[h] === undefined || r[h] === null ? "" : r[h]));
    const mine = cur ? String(cur[TXC["Your category"] - 1] || "") : "";
    if (mine && mine !== String(r.Answered || "")) answers[r.Key] = mine;   // you picked a category in the sheet
    if (cur) existing[i] = vals; else existing.push(vals);
  });
  const when = (v) => v instanceof Date ? v.getTime() : (Date.parse(String(v)) || 0);
  existing.sort((a, b) => when(a[0]) - when(b[0]));   // oldest at the top, like Orders
  sh.getRange(1, 1, 1, TX.length).setValues([TX]);
  if (width > TX.length) sh.getRange(1, TX.length + 1, 1, width - TX.length).clearContent();
  const need = existing.length + 201;
  if (sh.getMaxRows() < need) sh.insertRowsAfter(sh.getMaxRows(), need - sh.getMaxRows());
  sh.getRange(2, 1, sh.getMaxRows() - 1, Math.max(sh.getMaxColumns(), TX.length)).clearDataValidations();
  sh.getRange(2, 1, sh.getMaxRows() - 1, TX.length).clearContent();
  if (existing.length) sh.getRange(2, 1, existing.length, TX.length).setValues(existing);

  const rowsN = sh.getMaxRows() - 1;
  sh.setFrozenRows(1);
  sh.getRange(1, 1, sh.getMaxRows(), TX.length).setFontFamily("Arial").setFontSize(10).setVerticalAlignment("middle");
  sh.getRange(1, 1, 1, TX.length).setBackground("#2b2f45").setFontColor("#ffffff").setFontWeight("bold");
  TX_YOURS.forEach(h => sh.getRange(1, TXC[h]).setBackground("#5b4bd6"));
  sh.getRange(1, TXC["Your category"]).setNote("Pick a category to answer a question or correct one. The Command Centre learns the merchant for next time.");
  sh.getBandings().forEach(b => b.remove());
  sh.getRange(2, 1, rowsN, TX.length).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  sh.getRange(2, TXC.Amount, rowsN, 1).setNumberFormat("£#,##0.00;[Red]-£#,##0.00");
  sh.getRange(2, TXC.Category, rowsN, 1).setFontWeight("bold");
  sh.getRange(2, TXC["Your category"], rowsN, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(CATS, true).setAllowInvalid(false).build());
  const rg = (h) => sh.getRange(2, TXC[h], rowsN, 1);
  const L = (h) => letter_(TXC[h]);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied("=LEN($" + L("Question") + "2)>0").setBackground("#ffecc2").setFontColor("#7a4b00").setRanges([rg("Question")]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("Stock").setBackground("#cff3e2").setFontColor("#0b5d3b").setRanges([rg("Category")]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("Transfers").setFontColor("#9aa0b4").setRanges([rg("Category")]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied("=AND(LEN($" + L("Category") + "2)=0,LEN($" + L("Key") + "2)>0)").setBackground("#fbd5da").setFontColor("#8f1d2c").setRanges([rg("Category")]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied("=LEN($" + L("Your category") + "2)>0").setBackground("#e6e0fb").setRanges([rg("Your category")]).build(),
  ]);
  if (!sh.getFilter()) sh.getRange(1, 1, sh.getMaxRows(), TX.length).createFilter();
  const W = { "Date": 90, "Card / account": 150, "Merchant": 190, "Description": 230, "Amount": 90, "Original": 95, "Category": 150, "How": 110,
    "Matched order": 280, "Question": 300, "Your category": 160, "Note": 200, "Key": 60 };
  Object.entries(W).forEach(([h, w]) => sh.setColumnWidth(TXC[h], w));
  sh.getRange(2, TXC.Key, rowsN, 1).setFontColor("#9aa0b4").setFontSize(8);
  return { answers: answers, total: existing.length };
}

function out_(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }


// ---------- Deadlines & bookings -> Google Calendar (v6) ----------
// The Command Centre finds deadlines/appointments in your inboxes and sends them here. Each event is remembered by its key,
// so re-sending updates it instead of making a duplicate. Events you delete in Calendar are not re-created.
function calendar_(events, remove) {
  // its own "Deadlines" calendar (user's choice): hide/recolour/remove it all in one place
  const cal = CalendarApp.getCalendarsByName("Deadlines")[0] ||
              CalendarApp.createCalendar("Deadlines", { summary: "Bills, returns, renewals and bookings found in your email by the Command Centre", color: CalendarApp.Color.RED });
  const props = PropertiesService.getScriptProperties();
  const res = { ok: true, v: 6, created: 0, updated: 0, skipped: 0, removed: 0, ids: {} };
  events.forEach(ev => {
    const pk = "cal:" + ev.key;
    const known = props.getProperty(pk);
    if (known === "deleted") { res.skipped++; return; }
    let e = null;
    if (known) {
      try { e = cal.getEventById(known); } catch (err) { e = null; }
      if (!e || e.getTitle() === "") { props.setProperty(pk, "deleted"); res.skipped++; return; }   // you deleted it
    }
    const start = new Date(ev.start), end = new Date(ev.end);
    if (e) {
      if (e.getTitle() !== ev.title) e.setTitle(ev.title);
      if (e.getStartTime().getTime() !== start.getTime() || e.getEndTime().getTime() !== end.getTime()) e.setTime(start, end);
      e.setDescription(ev.description || "");
      res.updated++;
    } else {
      e = cal.createEvent(ev.title, start, end, { description: ev.description || "", location: ev.location || "" });
      e.removeAllReminders();
      (ev.reminders || []).slice(0, 5).forEach(m => e.addPopupReminder(m));
      e.setTag("commandCentre", ev.key);
      props.setProperty(pk, e.getId());
      res.created++;
    }
    res.ids[ev.key] = e.getId();
  });
  remove.forEach(k => {
    const id = props.getProperty("cal:" + k);
    if (id && id !== "deleted") { try { const e = cal.getEventById(id); if (e) e.deleteEvent(); } catch (err) {} }
    props.setProperty("cal:" + k, "deleted"); res.removed++;
  });
  return res;
}

// Run once from the editor (Run > authoriseCalendar) so Google asks for Calendar access
function authoriseCalendar() { CalendarApp.getDefaultCalendar().getName(); }
