"""Send daily Qullamaggie digest email via SMTP."""
from __future__ import annotations

import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scanner.patterns import Setup

logger = logging.getLogger(__name__)

SETUP_COLORS = {
    "EP":   "#7c3aed",
    "TB":   "#16a34a",
    "PP":   "#0891b2",
    "PULL": "#d97706",
    "FLAG": "#2563eb",
}


def _badge(setup_type: str) -> str:
    color = SETUP_COLORS.get(setup_type, "#6b7280")
    return (
        f'<span style="background:{color};color:#fff;'
        f'padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">'
        f'{setup_type}</span>'
    )


def _grade_color(grade: str) -> str:
    return {"A": "#16a34a", "B": "#2563eb", "C": "#d97706"}.get(grade, "#6b7280")


def build_html(setups: list["Setup"], scan_date: date | None = None) -> str:
    scan_date = scan_date or date.today()
    rows = ""
    for s in setups:
        rr_color = "#16a34a" if s.rr >= 2.0 else ("#d97706" if s.rr >= 1.5 else "#6b7280")
        rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 8px;font-weight:700;font-size:14px;">{s.symbol}</td>
          <td style="padding:10px 8px;">{_badge(s.setup_type)}</td>
          <td style="padding:10px 8px;text-align:right;">${s.entry:.2f}</td>
          <td style="padding:10px 8px;text-align:right;color:#dc2626;">${s.stop:.2f}</td>
          <td style="padding:10px 8px;text-align:right;">${s.t1:.2f}</td>
          <td style="padding:10px 8px;text-align:right;color:#16a34a;">${s.t2:.2f}</td>
          <td style="padding:10px 8px;text-align:right;color:{rr_color};font-weight:700;">{s.rr:.1f}x</td>
          <td style="padding:10px 8px;text-align:right;">{s.rs_score:.0f}</td>
          <td style="padding:10px 8px;text-align:center;color:{_grade_color(s.prob_grade)};font-weight:700;">P{s.prob_grade} <span style="color:#6b7280;font-weight:400;">{s.prob_score:.0f}</span></td>
          <td style="padding:10px 8px;color:#6b7280;font-size:12px;">{s.notes}</td>
        </tr>"""

    setup_count = len(setups)
    ep_count = sum(1 for s in setups if s.setup_type == "EP")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:900px;margin:24px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 100%);padding:28px 32px;color:#fff;">
      <h1 style="margin:0;font-size:22px;font-weight:700;">📈 Qullamaggie Daily Digest</h1>
      <p style="margin:6px 0 0;opacity:.75;font-size:14px;">{scan_date.strftime('%A, %B %d, %Y')}</p>
    </div>

    <!-- Summary bar -->
    <div style="background:#f8f7ff;border-bottom:1px solid #e5e7eb;padding:14px 32px;display:flex;gap:32px;">
      <div><span style="font-size:24px;font-weight:800;color:#1e1b4b;">{setup_count}</span>
           <span style="font-size:13px;color:#6b7280;margin-left:4px;">setups found</span></div>
      <div><span style="font-size:24px;font-weight:800;color:#7c3aed;">{ep_count}</span>
           <span style="font-size:13px;color:#6b7280;margin-left:4px;">Episodic Pivots</span></div>
    </div>

    <!-- Table -->
    <div style="padding:24px 32px;overflow-x:auto;">
      {'<p style="color:#6b7280;text-align:center;padding:32px 0;">No setups matched today\'s criteria. Markets may be in a consolidation phase.</p>' if not setups else f"""
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f9fafb;color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:.05em;">
            <th style="padding:8px;text-align:left;">Symbol</th>
            <th style="padding:8px;text-align:left;">Setup</th>
            <th style="padding:8px;text-align:right;">Entry</th>
            <th style="padding:8px;text-align:right;">Stop</th>
            <th style="padding:8px;text-align:right;">T1</th>
            <th style="padding:8px;text-align:right;">T2</th>
            <th style="padding:8px;text-align:right;">R:R</th>
            <th style="padding:8px;text-align:right;">RS</th>
            <th style="padding:8px;text-align:center;">P Score</th>
            <th style="padding:8px;text-align:left;">Notes</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>"""}
    </div>

    <!-- Legend -->
    <div style="padding:0 32px 24px;border-top:1px solid #f3f4f6;margin-top:8px;">
      <p style="font-size:11px;color:#9ca3af;margin:16px 0 4px;">
        <strong>EP</strong>=Episodic Pivot &nbsp;
        <strong>TB</strong>=Tight Base &nbsp;
        <strong>PP</strong>=Pocket Pivot &nbsp;
        <strong>PULL</strong>=EMA21 Pullback &nbsp;
        &nbsp;|&nbsp; <strong>RS</strong>=Relative Strength vs SPY (0–100) &nbsp;
        &nbsp;|&nbsp; Entry/Stop/T1/T2 are levels — confirm on chart before trading.
      </p>
    </div>

    <!-- Footer -->
    <div style="background:#f3f4f6;padding:16px 32px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#9ca3af;">
        Qullamaggie Platform &nbsp;·&nbsp; Generated {scan_date.isoformat()} &nbsp;·&nbsp;
        Not financial advice. Always do your own research.
      </p>
    </div>
  </div>
</body>
</html>"""


def send_digest(
    setups: list["Setup"],
    to_email: str,
    from_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    use_tls: bool = True,
) -> None:
    today = date.today()
    subject = f"Qullamaggie Digest {today.isoformat()} — {len(setups)} setup{'s' if len(setups) != 1 else ''}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    html_body = build_html(setups, today)
    msg.attach(MIMEText(html_body, "html"))

    try:
        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())
        logger.info("Digest sent to %s (%d setups)", to_email, len(setups))
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        raise
