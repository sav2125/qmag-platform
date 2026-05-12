"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [testStatus, setTestStatus] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [testMsg, setTestMsg] = useState("");
  const [digestStatus, setDigestStatus] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [digestMsg, setDigestMsg] = useState("");

  const [universe, setUniverse] = useState("sp500");
  const [minRs, setMinRs] = useState(50);
  const [top, setTop] = useState(20);

  async function sendTest() {
    setTestStatus("sending");
    try {
      const r = await api.testEmail();
      setTestStatus("ok");
      setTestMsg(`Test email sent to ${r.to}`);
    } catch (e) {
      setTestStatus("error");
      setTestMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  async function sendDigest() {
    setDigestStatus("sending");
    try {
      const r = await api.sendDigest({ universe, min_rs: minRs, top });
      setDigestStatus("ok");
      setDigestMsg(`Digest sent to ${r.to} — ${r.setups} setup${r.setups !== 1 ? "s" : ""}`);
    } catch (e) {
      setDigestStatus("error");
      setDigestMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Email notifications and daily digest configuration.</p>
      </div>

      {/* Email config instructions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-3">
        <h2 className="font-semibold text-gray-800">Email Configuration</h2>
        <p className="text-sm text-gray-500">
          Set the following variables in <code className="bg-gray-100 px-1 rounded text-xs">backend/.env</code>:
        </p>
        <pre className="bg-gray-950 text-green-400 rounded-lg p-4 text-xs overflow-x-auto">{`NOTIFY_TO_EMAIL=you@example.com
NOTIFY_FROM_EMAIL=yourapp@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourapp@gmail.com
SMTP_PASSWORD=your-gmail-app-password`}</pre>
        <p className="text-xs text-gray-400">
          For Gmail, generate an <strong>App Password</strong> at
          {" "}<a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener"
            className="text-indigo-500 underline">myaccount.google.com/apppasswords</a>
          {" "}(requires 2FA enabled).
        </p>
      </div>

      {/* Test email */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Test Email</h2>
        <p className="text-sm text-gray-500">Sends a sample digest with mock data to verify your SMTP config.</p>
        <button onClick={sendTest} disabled={testStatus === "sending"}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-lg px-5 py-2 text-sm transition-colors">
          {testStatus === "sending" ? "Sending…" : "Send Test Email"}
        </button>
        {testStatus === "ok" && <p className="text-green-600 text-sm">✓ {testMsg}</p>}
        {testStatus === "error" && <p className="text-red-500 text-sm">✗ {testMsg}</p>}
      </div>

      {/* Manual digest */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Send Digest Now</h2>
        <p className="text-sm text-gray-500">Run a live scan and email the results immediately.</p>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Universe</label>
            <select value={universe} onChange={(e) => setUniverse(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
              {["sp500", "tech", "watchlist"].map((u) => <option key={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Min RS ({minRs})</label>
            <input type="range" min={0} max={90} step={5} value={minRs}
              onChange={(e) => setMinRs(Number(e.target.value))}
              className="w-full accent-indigo-600 mt-2" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Top N</label>
            <input type="number" min={5} max={50} value={top}
              onChange={(e) => setTop(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
        </div>
        <button onClick={sendDigest} disabled={digestStatus === "sending"}
          className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-lg px-5 py-2 text-sm transition-colors">
          {digestStatus === "sending" ? "Scanning & Sending…" : "Send Digest Now"}
        </button>
        {digestStatus === "ok" && <p className="text-green-600 text-sm">✓ {digestMsg}</p>}
        {digestStatus === "error" && <p className="text-red-500 text-sm">✗ {digestMsg}</p>}
      </div>

      {/* Daily routine info */}
      <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-5 space-y-2">
        <h2 className="font-semibold text-indigo-900">Daily Routine</h2>
        <p className="text-sm text-indigo-700">
          A scheduled routine runs every weekday at <strong>7:00 AM ET</strong> to scan the market
          and send your digest automatically. The routine was set up via the Claude Code schedule skill.
        </p>
        <p className="text-xs text-indigo-400">
          To change the time or universe, re-run <code className="bg-indigo-100 px-1 rounded">schedule</code> from your terminal.
        </p>
      </div>
    </div>
  );
}
