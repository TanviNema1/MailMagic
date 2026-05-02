import { useState, useEffect, useRef } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
} from "recharts";

// ─── Seed Data ───────────────────────────────────────────────────────────────
const CUSTOMERS = [
  { id: 1, name: "Aria Fontaine", email: "aria@example.com", tier: "Platinum", tag: "Tech", score: 0.92, lastOpen: "2h ago" },
  { id: 2, name: "Marcus Webb", email: "marcus@example.com", tier: "Gold", tag: "Fashion", score: 0.78, lastOpen: "1d ago" },
  { id: 3, name: "Yuki Tanaka", email: "yuki@example.com", tier: "Silver", tag: "Fitness", score: 0.61, lastOpen: "3d ago" },
  { id: 4, name: "Devon Okafor", email: "devon@example.com", tier: "Platinum", tag: "Finance", score: 0.88, lastOpen: "5h ago" },
  { id: 5, name: "Celeste Morin", email: "celeste@example.com", tier: "Gold", tag: "Travel", score: 0.74, lastOpen: "2d ago" },
  { id: 6, name: "Rafe Holloway", email: "rafe@example.com", tier: "Bronze", tag: "Tech", score: 0.45, lastOpen: "7d ago" },
  { id: 7, name: "Priya Nair", email: "priya@example.com", tier: "Silver", tag: "Wellness", score: 0.67, lastOpen: "4d ago" },
  { id: 8, name: "Jonah Steele", email: "jonah@example.com", tier: "Platinum", tag: "Finance", score: 0.91, lastOpen: "1h ago" },
];

const HEATMAP_DATA = [
  { hour: "6am", sends: 12 }, { hour: "7am", sends: 28 }, { hour: "8am", sends: 54 },
  { hour: "9am", sends: 87 }, { hour: "10am", sends: 63 }, { hour: "11am", sends: 42 },
  { hour: "12pm", sends: 35 }, { hour: "1pm", sends: 29 }, { hour: "2pm", sends: 44 },
  { hour: "3pm", sends: 58 }, { hour: "4pm", sends: 71 }, { hour: "5pm", sends: 48 },
  { hour: "6pm", sends: 22 }, { hour: "7pm", sends: 15 },
];

const PIE_DATA = [
  { name: "Tech", value: 34, color: "#00f5c4" },
  { name: "Finance", value: 28, color: "#7b61ff" },
  { name: "Fashion", value: 18, color: "#ff6b9d" },
  { name: "Fitness", value: 12, color: "#ffd166" },
  { name: "Travel", value: 8, color: "#06d6a0" },
];

const SENTIMENT_DATA = [
  { week: "W1", score: 72 }, { week: "W2", score: 75 }, { week: "W3", score: 69 },
  { week: "W4", score: 81 }, { week: "W5", score: 84 }, { week: "W6", score: 88 },
  { week: "W7", score: 91 }, { week: "W8", score: 87 },
];

const TIER_COLORS = { Platinum: "#e5c97e", Gold: "#ffd166", Silver: "#aab4c8", Bronze: "#cd7f32" };

const FAKE_EMAILS = {
  "Aria Fontaine": {
    subject: "Your exclusive Tech preview, Aria",
    body: `Hi Aria,

As one of our most valued Platinum members, we wanted to give you first access to something special.

We've curated a selection of cutting-edge tech drops based on your browsing history — including the items you added to your wishlist last Tuesday. Based on your engagement patterns, we predict you're most likely to love these between 9–10am.

Your personalized picks are waiting. Tap below to claim your early access window before it closes at midnight.

With excitement,
The MailMagic Team`
  },
  "Jonah Steele": {
    subject: "Jonah, your portfolio just unlocked this",
    body: `Hi Jonah,

Your Platinum status opens doors others don't see yet.

We've analyzed the Finance content you engage with most, and we've prepared a special brief: market movers for the week, curated exclusively for members with your profile. Delivered right on time — our model places your peak engagement at 8am Tuesdays.

One click. Full access. Zero noise.

Best,
The MailMagic Team`
  }
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ─── Sub-components ──────────────────────────────────────────────────────────
function Pill({ label, color }) {
  return (
    <span style={{
      background: color + "22", color, border: `1px solid ${color}44`,
      borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600,
      letterSpacing: "0.05em", whiteSpace: "nowrap"
    }}>{label}</span>
  );
}

function ScoreBar({ value }) {
  const color = value > 0.8 ? "#00f5c4" : value > 0.6 ? "#ffd166" : "#ff6b9d";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, background: "#1a1f2e", borderRadius: 99, height: 6, overflow: "hidden" }}>
        <div style={{ width: `${value * 100}%`, height: "100%", background: color, borderRadius: 99, transition: "width 0.8s ease" }} />
      </div>
      <span style={{ color, fontSize: 12, fontWeight: 700, minWidth: 32 }}>{Math.round(value * 100)}%</span>
    </div>
  );
}

function StatusLine({ text, done }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", opacity: done ? 1 : 0.5, transition: "opacity 0.4s" }}>
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: done ? "#00f5c4" : "#7b61ff",
        boxShadow: done ? "0 0 8px #00f5c4" : "none",
        flexShrink: 0
      }} />
      <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: done ? "#e0e6f7" : "#6b7a99" }}>{text}</span>
    </div>
  );
}

function KPICard({ label, value, sub, accent }) {
  return (
    <div style={{
      background: "#10131c", border: "1px solid #1e2538", borderRadius: 12,
      padding: "20px 24px", flex: 1, minWidth: 140
    }}>
      <div style={{ fontSize: 11, color: "#6b7a99", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 36, fontWeight: 800, color: accent || "#00f5c4", fontFamily: "'Space Mono', monospace", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "#6b7a99", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────
function EmailModal({ customer, onClose, onApprove }) {
  const email = FAKE_EMAILS[customer.name] || {
    subject: `${customer.tag} update just for you, ${customer.name.split(" ")[0]}`,
    body: `Hi ${customer.name.split(" ")[0]},\n\nWe've crafted something special for you as a ${customer.tier} member...\n\nBest,\nThe MailMagic Team`
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)",
      zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center"
    }} onClick={onClose}>
      <div style={{
        background: "#10131c", border: "1px solid #00f5c433", borderRadius: 16,
        width: "min(600px, 92vw)", padding: 32, position: "relative",
        boxShadow: "0 0 60px #00f5c422"
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#00f5c4", boxShadow: "0 0 10px #00f5c4" }} />
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#00f5c4", letterSpacing: "0.1em" }}>AI-GENERATED PREVIEW</span>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#6b7a99", cursor: "pointer", fontSize: 20 }}>✕</button>
        </div>
        <div style={{ marginBottom: 6, fontSize: 11, color: "#6b7a99" }}>TO</div>
        <div style={{ color: "#e0e6f7", marginBottom: 16 }}>{customer.name} &lt;{customer.email}&gt;</div>
        <div style={{ marginBottom: 6, fontSize: 11, color: "#6b7a99" }}>SUBJECT</div>
        <div style={{ color: "#fff", fontWeight: 700, fontSize: 16, marginBottom: 20 }}>{email.subject}</div>
        <div style={{
          background: "#0d0f18", border: "1px solid #1e2538", borderRadius: 10,
          padding: 20, fontFamily: "'IBM Plex Mono', monospace", fontSize: 13,
          color: "#c0c8dc", lineHeight: 1.8, whiteSpace: "pre-wrap", marginBottom: 24,
          maxHeight: 260, overflowY: "auto"
        }}>{email.body}</div>
        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{
            background: "none", border: "1px solid #1e2538", color: "#6b7a99",
            padding: "10px 20px", borderRadius: 8, cursor: "pointer", fontFamily: "'Space Mono', monospace", fontSize: 12
          }}>Discard</button>
          <button onClick={() => { onApprove(customer); onClose(); }} style={{
            background: "linear-gradient(135deg, #00f5c4, #7b61ff)", border: "none",
            color: "#0d0f18", fontWeight: 800, padding: "10px 24px", borderRadius: 8,
            cursor: "pointer", fontFamily: "'Space Mono', monospace", fontSize: 12, letterSpacing: "0.05em"
          }}>✓ Approve &amp; Send</button>
        </div>
      </div>
    </div>
  );
}

// ─── Tab 1: Campaign ─────────────────────────────────────────────────────────
function CampaignTab() {
  const [selected, setSelected] = useState(new Set());
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("All");
  const [running, setRunning] = useState(false);
  const [statusLines, setStatusLines] = useState([]);
  const [currentCustomer, setCurrentCustomer] = useState(null);
  const [modal, setModal] = useState(null);
  const [sent, setSent] = useState(new Set());

  const tiers = ["All", "Platinum", "Gold", "Silver", "Bronze"];
  const filtered = CUSTOMERS.filter(c =>
    (tierFilter === "All" || c.tier === tierFilter) &&
    (c.name.toLowerCase().includes(search.toLowerCase()) || c.tag.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleSelect = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map(c => c.id)));
  };

  const runMagic = async () => {
    const targets = CUSTOMERS.filter(c => selected.has(c.id));
    if (!targets.length) return;
    setRunning(true);
    setStatusLines([]);
    for (const c of targets) {
      setCurrentCustomer(c.name);
      setStatusLines(prev => [...prev, { text: `Calculating optimal send time for ${c.name} using XGBoost...`, done: false }]);
      await sleep(1000);
      setStatusLines(prev => prev.map((l, i) => i === prev.length - 1 ? { ...l, done: true } : l));
      setStatusLines(prev => [...prev, { text: `Generating personalized copy for ${c.name} using Gemini...`, done: false }]);
      await sleep(1200);
      setStatusLines(prev => prev.map((l, i) => i === prev.length - 1 ? { ...l, done: true } : l));
      setStatusLines(prev => [...prev, { text: `Email ready — awaiting your approval for ${c.name}`, done: true }]);
      await sleep(400);
      setModal(c);
      await new Promise(res => {
        const check = setInterval(() => { if (!document.querySelector("[data-modal]")) { clearInterval(check); res(); } }, 300);
      });
      await sleep(300);
    }
    setCurrentCustomer(null);
    setRunning(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Controls */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#6b7a99", fontSize: 14 }}>⌕</span>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or interest..."
            style={{
              width: "100%", background: "#10131c", border: "1px solid #1e2538", borderRadius: 8,
              padding: "10px 12px 10px 34px", color: "#e0e6f7", fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 13, outline: "none", boxSizing: "border-box"
            }} />
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {tiers.map(t => (
            <button key={t} onClick={() => setTierFilter(t)} style={{
              background: tierFilter === t ? "#7b61ff22" : "none",
              border: `1px solid ${tierFilter === t ? "#7b61ff" : "#1e2538"}`,
              color: tierFilter === t ? "#7b61ff" : "#6b7a99",
              padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 12,
              fontFamily: "'Space Mono', monospace"
            }}>{t}</button>
          ))}
        </div>
        <button onClick={runMagic} disabled={running || selected.size === 0} style={{
          background: selected.size > 0 && !running ? "linear-gradient(135deg, #00f5c4, #7b61ff)" : "#1e2538",
          border: "none", color: selected.size > 0 && !running ? "#0d0f18" : "#6b7a99",
          fontWeight: 800, padding: "10px 24px", borderRadius: 8, cursor: selected.size > 0 && !running ? "pointer" : "default",
          fontFamily: "'Space Mono', monospace", fontSize: 13, letterSpacing: "0.05em",
          transition: "all 0.3s", whiteSpace: "nowrap"
        }}>
          {running ? "⟳ Running..." : `✦ Run Magic${selected.size > 0 ? ` (${selected.size})` : ""}`}
        </button>
      </div>

      {/* Table */}
      <div style={{ background: "#10131c", border: "1px solid #1e2538", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #1e2538" }}>
              <th style={{ padding: "12px 16px", textAlign: "left", width: 36 }}>
                <input type="checkbox" checked={selected.size === filtered.length && filtered.length > 0}
                  onChange={toggleAll} style={{ accentColor: "#00f5c4", cursor: "pointer" }} />
              </th>
              {["Customer", "Tier", "Interest", "Engage Score", "Last Open", "Status"].map(h => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: 11, color: "#6b7a99", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={c.id} style={{
                borderBottom: "1px solid #1a1f2e",
                background: selected.has(c.id) ? "#7b61ff11" : "transparent",
                transition: "background 0.2s"
              }}>
                <td style={{ padding: "14px 16px" }}>
                  <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)}
                    style={{ accentColor: "#7b61ff", cursor: "pointer" }} />
                </td>
                <td style={{ padding: "14px 16px" }}>
                  <div style={{ fontWeight: 600, color: "#e0e6f7", fontSize: 14 }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: "#6b7a99", marginTop: 2 }}>{c.email}</div>
                </td>
                <td style={{ padding: "14px 16px" }}>
                  <Pill label={c.tier} color={TIER_COLORS[c.tier]} />
                </td>
                <td style={{ padding: "14px 16px" }}>
                  <Pill label={c.tag} color="#7b61ff" />
                </td>
                <td style={{ padding: "14px 16px", minWidth: 120 }}>
                  <ScoreBar value={c.score} />
                </td>
                <td style={{ padding: "14px 16px", fontSize: 12, color: "#6b7a99" }}>{c.lastOpen}</td>
                <td style={{ padding: "14px 16px" }}>
                  {sent.has(c.id)
                    ? <Pill label="✓ Sent" color="#00f5c4" />
                    : <Pill label="Pending" color="#6b7a99" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Status feed */}
      {statusLines.length > 0 && (
        <div style={{ background: "#0d0f18", border: "1px solid #1e2538", borderRadius: 10, padding: "16px 20px" }}>
          <div style={{ fontSize: 11, color: "#7b61ff", fontFamily: "'Space Mono', monospace", letterSpacing: "0.1em", marginBottom: 10 }}>
            ◈ LIVE EXECUTION LOG
          </div>
          {statusLines.map((l, i) => <StatusLine key={i} text={l.text} done={l.done} />)}
        </div>
      )}

      {modal && (
        <div data-modal>
          <EmailModal customer={modal} onClose={() => setModal(null)} onApprove={(c) => setSent(prev => new Set([...prev, c.id]))} />
        </div>
      )}
    </div>
  );
}

// ─── Tab 2: Analytics ─────────────────────────────────────────────────────────
function AnalyticsTab() {
  const customTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: "#10131c", border: "1px solid #1e2538", borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ color: "#6b7a99", fontSize: 11, marginBottom: 4 }}>{label}</div>
          <div style={{ color: "#00f5c4", fontFamily: "'Space Mono', monospace", fontWeight: 700 }}>{payload[0].value}</div>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* KPI Row */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <KPICard label="Total Sent" value="1,284" sub="↑ 18% vs last month" accent="#00f5c4" />
        <KPICard label="Open Rate" value="38.2%" sub="Predicted: 35.1% · Actual: 38.2%" accent="#7b61ff" />
        <KPICard label="Engagement Lift" value="+8.7%" sub="vs. non-optimized baseline" accent="#ffd166" />
        <KPICard label="Avg Quality Score" value="87/100" sub="AI copy sentiment score" accent="#ff6b9d" />
      </div>

      {/* Charts row 1 */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        {/* Heatmap */}
        <div style={{ flex: 2, minWidth: 300, background: "#10131c", border: "1px solid #1e2538", borderRadius: 12, padding: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e6f7", marginBottom: 4 }}>Send-Time Distribution</div>
          <div style={{ fontSize: 11, color: "#6b7a99", marginBottom: 20 }}>Optimal hours predicted by XGBoost model</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={HEATMAP_DATA} barSize={22}>
              <XAxis dataKey="hour" tick={{ fill: "#6b7a99", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip content={customTooltip} cursor={{ fill: "#ffffff08" }} />
              <Bar dataKey="sends" radius={[4, 4, 0, 0]}>
                {HEATMAP_DATA.map((entry, i) => (
                  <Cell key={i} fill={entry.sends > 60 ? "#00f5c4" : entry.sends > 35 ? "#7b61ff" : "#1e2538"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie */}
        <div style={{ flex: 1, minWidth: 240, background: "#10131c", border: "1px solid #1e2538", borderRadius: 12, padding: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e6f7", marginBottom: 4 }}>Interest Breakdown</div>
          <div style={{ fontSize: 11, color: "#6b7a99", marginBottom: 16 }}>Click share by interest tag</div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={PIE_DATA} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3}>
                {PIE_DATA.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip formatter={(v, n) => [`${v}%`, n]} contentStyle={{ background: "#10131c", border: "1px solid #1e2538", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {PIE_DATA.map(d => (
              <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: d.color }} />
                <span style={{ fontSize: 11, color: "#6b7a99" }}>{d.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sentiment trend */}
      <div style={{ background: "#10131c", border: "1px solid #1e2538", borderRadius: 12, padding: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e6f7", marginBottom: 4 }}>AI Copy Quality Score — Trend</div>
        <div style={{ fontSize: 11, color: "#6b7a99", marginBottom: 20 }}>Weekly Gemini-generated email sentiment & clarity score</div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={SENTIMENT_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2538" />
            <XAxis dataKey="week" tick={{ fill: "#6b7a99", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis domain={[60, 100]} tick={{ fill: "#6b7a99", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#10131c", border: "1px solid #1e2538", borderRadius: 8 }} />
            <Line type="monotone" dataKey="score" stroke="#00f5c4" strokeWidth={2.5} dot={{ fill: "#00f5c4", r: 4 }} activeDot={{ r: 6, fill: "#fff" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("campaign");
  const [dark, setDark] = useState(true);
  const [geminiOk] = useState(true);
  const [gmailOk] = useState(true);
  const [temperature, setTemperature] = useState(0.72);
  const [model] = useState("xgboost-v3.1");

  return (
    <div style={{
      minHeight: "100vh", background: dark ? "#0d0f18" : "#f0f2fa",
      color: dark ? "#e0e6f7" : "#0d0f18",
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
      transition: "background 0.3s, color 0.3s"
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: #10131c; }
        ::-webkit-scrollbar-thumb { background: #2a3050; border-radius: 99px; }
        input[type=range] { accent-color: #7b61ff; }
      `}</style>

      {/* Sidebar */}
      <div style={{
        position: "fixed", left: 0, top: 0, bottom: 0, width: 240,
        background: dark ? "#0a0c14" : "#fff",
        borderRight: `1px solid ${dark ? "#1e2538" : "#e2e6f0"}`,
        padding: "24px 0", display: "flex", flexDirection: "column", zIndex: 100
      }}>
        {/* Logo */}
        <div style={{ padding: "0 20px 28px" }}>
          <div style={{ fontFamily: "'Space Mono', monospace", fontWeight: 700, fontSize: 20, color: "#00f5c4", letterSpacing: "-0.02em" }}>
            Mail<span style={{ color: "#7b61ff" }}>Magic</span>
          </div>
          <div style={{ fontSize: 10, color: "#6b7a99", letterSpacing: "0.1em", marginTop: 2 }}>AI EMAIL PLATFORM</div>
        </div>

        {/* API Status */}
        <div style={{ padding: "0 20px 24px", borderBottom: `1px solid ${dark ? "#1e2538" : "#e2e6f0"}`, marginBottom: 20 }}>
          <div style={{ fontSize: 10, color: "#6b7a99", letterSpacing: "0.1em", marginBottom: 10 }}>API STATUS</div>
          {[["Gemini API", geminiOk], ["Gmail API", gmailOk]].map(([name, ok]) => (
            <div key={name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: dark ? "#aab4c8" : "#333" }}>{name}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: ok ? "#00f5c4" : "#ff6b9d", boxShadow: ok ? "0 0 6px #00f5c4" : "0 0 6px #ff6b9d" }} />
                <span style={{ fontSize: 10, color: ok ? "#00f5c4" : "#ff6b9d", fontFamily: "'Space Mono', monospace" }}>{ok ? "LIVE" : "DOWN"}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Model settings */}
        <div style={{ padding: "0 20px 24px", borderBottom: `1px solid ${dark ? "#1e2538" : "#e2e6f0"}`, marginBottom: 20 }}>
          <div style={{ fontSize: 10, color: "#6b7a99", letterSpacing: "0.1em", marginBottom: 12 }}>MODEL SETTINGS</div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: dark ? "#aab4c8" : "#555" }}>Temperature</span>
              <span style={{ fontSize: 11, fontFamily: "'Space Mono', monospace", color: "#7b61ff" }}>{temperature.toFixed(2)}</span>
            </div>
            <input type="range" min={0} max={1} step={0.01} value={temperature}
              onChange={e => setTemperature(parseFloat(e.target.value))}
              style={{ width: "100%", cursor: "pointer" }} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: dark ? "#aab4c8" : "#555", marginBottom: 6 }}>XGBoost Model</div>
            <div style={{
              background: dark ? "#10131c" : "#f0f2fa", border: `1px solid ${dark ? "#1e2538" : "#dde1ec"}`,
              borderRadius: 6, padding: "7px 10px",
              fontSize: 11, fontFamily: "'Space Mono', monospace", color: "#00f5c4"
            }}>{model}</div>
          </div>
        </div>

        {/* Theme */}
        <div style={{ padding: "0 20px", marginTop: "auto" }}>
          <button onClick={() => setDark(d => !d)} style={{
            width: "100%", background: dark ? "#10131c" : "#e8ebf5",
            border: `1px solid ${dark ? "#1e2538" : "#dde1ec"}`,
            borderRadius: 8, padding: "10px 14px", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            color: dark ? "#aab4c8" : "#555", fontSize: 12
          }}>
            <span>{dark ? "🌙 Dark Mode" : "☀️ Light Mode"}</span>
            <div style={{
              width: 36, height: 20, borderRadius: 99, position: "relative",
              background: dark ? "#7b61ff" : "#e2e6f0", transition: "background 0.3s"
            }}>
              <div style={{
                position: "absolute", top: 3, left: dark ? 18 : 3, width: 14, height: 14,
                borderRadius: "50%", background: "#fff", transition: "left 0.3s"
              }} />
            </div>
          </button>
        </div>
      </div>

      {/* Main */}
      <div style={{ marginLeft: 240, padding: 32 }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{
            fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700,
            margin: 0, letterSpacing: "-0.02em"
          }}>
            {tab === "campaign" ? "Campaign Execution" : "Analytics & Insights"}
          </h1>
          <p style={{ color: "#6b7a99", margin: "6px 0 0", fontSize: 14 }}>
            {tab === "campaign" ? "Select leads, run AI generation, review & send." : "Performance metrics across campaigns and send times."}
          </p>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 28, background: dark ? "#10131c" : "#fff", border: `1px solid ${dark ? "#1e2538" : "#e2e6f0"}`, borderRadius: 10, padding: 4, width: "fit-content" }}>
          {[["campaign", "✦ Campaign"], ["analytics", "◈ Analytics"]].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{
              background: tab === key ? (dark ? "#1e2538" : "#f0f2fa") : "none",
              border: "none", color: tab === key ? (dark ? "#e0e6f7" : "#0d0f18") : "#6b7a99",
              padding: "9px 20px", borderRadius: 7, cursor: "pointer", fontWeight: tab === key ? 700 : 400,
              fontSize: 13, fontFamily: "'Space Mono', monospace", transition: "all 0.2s",
              letterSpacing: "0.02em"
            }}>{label}</button>
          ))}
        </div>

        {tab === "campaign" ? <CampaignTab /> : <AnalyticsTab />}
      </div>
    </div>
  );
}
