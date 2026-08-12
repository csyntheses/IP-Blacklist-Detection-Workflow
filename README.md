# Breakout IP Blacklist Monitor

An automated IP reputation monitoring system that checks a breakout/egress IP against AbuseIPDB and alerts a SOC team via Microsoft Teams when the abuse confidence score exceeds a defined threshold.

Built for an ISP (FTTH) environment where a shared CGNAT breakout IP serves multiple residential subscribers — meaning abuse reports often trace to a single customer device, not systemic infrastructure issues. Early detection of blacklisting enables rapid subscriber-level remediation before deliverability or reputation damage spreads.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Scheduler   │────▶│  AbuseIPDB API   │────▶│  Threshold  │────▶│  Teams Webhook   │
│  (6-hour     │     │  /api/v2/check   │     │  Check      │     │  (Power Automate)│
│   interval)  │     │  (verbose mode)  │     │  score > 27 │     │                  │
└─────────────┘     └──────────────────┘     └─────────────┘     └─────────────────┘
```

## Alert Output

When triggered, the SOC team receives a Teams message containing:

- **Abuse confidence score** and total report count
- **Timestamp of the most recent report** (for cross-referencing NAT session logs to identify the subscriber)
- **Direct links** to AbuseIPDB history, takedown request form, and a comprehensive 200+ blacklist check via MultiRBL

## Why AbuseIPDB (and not MXToolbox or raw DNSBL scraping)

This project evaluated several approaches before settling on AbuseIPDB:

| Approach | Outcome |
|----------|---------|
| **MXToolbox API** | Free tier provides 0 Network Requests (the quota type blacklist checks consume). Paid tier required. |
| **Raw DNSBL queries via DNS-over-HTTPS** | Works for SpamRATS, HostKarma, Barracuda. Fails for Spamhaus — their public mirrors block queries routed through open/public resolvers (Google DoH, Cloudflare), returning `127.255.255.254` instead of real results. |
| **MultiRBL.valli.org scraping** | `robots.txt` explicitly disallows automated access. Respecting that. |
| **MXToolbox SuperTool scraping** | JavaScript-rendered page — no results in raw HTML, requires headless browser. |
| **AbuseIPDB `/api/v2/check`** | 1,000 free checks/day, real API with JSON responses, verbose mode includes per-report detail (timestamps, categories, comments). Clear winner. |

## Key Technical Decisions

- **Threshold set to score > 27**: The monitored IP currently sits at 27 (baseline noise for a shared FTTH breakout IP with 15 reports from 12 distinct reporters). Alerts fire only when the score *rises above* this baseline, indicating genuinely new abuse activity.
- **Verbose mode enabled**: The `&verbose` flag returns the full `reports` array, giving the analyst actual report timestamps and comments to cross-reference against NAT session logs — turning a bare score into an actionable lead on which subscriber to investigate.
- **MultiRBL included as manual deep-dive link**: While automation against MultiRBL isn't possible (robots.txt), including the direct lookup URL in every alert gives the analyst a one-click path to a comprehensive 200+ blacklist check for broader context.
- **Spamhaus check excluded from automation**: Their DNSBL infrastructure blocks queries from public DNS resolvers entirely. Included as a manual reference link (`check.spamhaus.org`) instead. See `docs/spamhaus-dnsbl-notes.md` for the full technical write-up.

## Repository Structure

```
├── README.md                          # This file
├── scripts/
│   ├── monitor.py                     # Standalone Python monitoring script
│   ├── config.example.env             # Environment variable template
│   └── test_abuseipdb.ps1             # PowerShell script used during development/testing
├── docs/
│   ├── spamhaus-dnsbl-notes.md        # Technical notes on Spamhaus DNSBL restrictions
│   └── takedown-template.md           # ISP takedown request template for AbuseIPDB
└── shuffle/
    └── workflow-overview.md           # Shuffle SOAR workflow documentation
```

## Quick Start

### Prerequisites

- Python 3.8+
- An [AbuseIPDB](https://www.abuseipdb.com/) account (free tier, 1,000 checks/day)
- A Microsoft Teams incoming webhook URL (via Power Automate Workflows)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/breakout-ip-monitor.git
cd breakout-ip-monitor/scripts

# Copy and edit the config
cp config.example.env .env
# Edit .env with your API key, webhook URL, IP, and threshold

# Install dependencies
pip install requests python-dotenv

# Run once manually
python monitor.py

# Or schedule with cron (every 6 hours)
# 0 */6 * * * cd /path/to/scripts && python monitor.py
```

## SOAR Implementation

This project was also implemented as a Shuffle SOAR workflow for GUI-based orchestration. See `shuffle/workflow-overview.md` for the full workflow documentation, node configuration, and condition logic.

## Takedown Process

When an alert fires, the analyst should:

1. Review the specific reports on AbuseIPDB (link in alert) — note timestamps and abuse categories
2. Cross-reference report timestamps against NAT session logs to identify the subscriber session
3. Take subscriber-level action (notification, remediation guidance, or service suspension)
4. If reports are stale/incorrect, submit a takedown request using the template in `docs/takedown-template.md`
5. Run the comprehensive MultiRBL check (link in alert) for broader blacklist context

## License

MIT
