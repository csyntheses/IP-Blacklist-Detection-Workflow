"""
Breakout IP Blacklist Monitor

Checks an IP against AbuseIPDB's abuse database and sends a formatted
alert to a Microsoft Teams channel (via Power Automate webhook) when the
abuse confidence score exceeds a configured threshold.

Designed for ISP/FTTH environments where a shared CGNAT breakout IP serves
multiple subscribers — abuse reports often trace to a single customer device,
so the alert includes report timestamps for cross-referencing NAT session logs.

Usage:
    python monitor.py              # Run once (e.g., from cron)
    python monitor.py --dry-run    # Check score, print alert, don't send

Environment variables (or .env file):
    ABUSEIPDB_API_KEY   - Your AbuseIPDB API key
    TEAMS_WEBHOOK_URL   - Power Automate incoming webhook URL
    MONITOR_IP          - The breakout IP to monitor
    SCORE_THRESHOLD     - Alert when score exceeds this value (default: 27)
    MAX_AGE_DAYS        - How far back to look for reports (default: 90)
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install it with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional — env vars can be set directly

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Configuration -----------------------------------------------------------

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
MONITOR_IP = os.getenv("MONITOR_IP", "")
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "27"))
MAX_AGE_DAYS = int(os.getenv("MAX_AGE_DAYS", "90"))

ABUSEIPDB_CHECK_URL = "https://api.abuseipdb.com/api/v2/check"

# AbuseIPDB category codes mapped to human-readable names
ABUSE_CATEGORIES = {
    1: "DNS Compromise",
    2: "DNS Poisoning",
    3: "Fraud Orders",
    4: "DDoS Attack",
    5: "FTP Brute-Force",
    6: "Ping of Death",
    7: "Phishing",
    8: "Fraud VoIP",
    9: "Open Proxy",
    10: "Web Spam",
    11: "Email Spam",
    12: "Blog Spam",
    13: "VPN IP",
    14: "Port Scan",
    15: "Hacking",
    16: "SQL Injection",
    17: "Spoofing",
    18: "Brute-Force",
    19: "Bad Web Bot",
    20: "Exploited Host",
    21: "Web App Attack",
    22: "SSH",
    23: "IoT Targeted",
}


def validate_config():
    """Ensure all required config values are present."""
    missing = []
    if not ABUSEIPDB_API_KEY:
        missing.append("ABUSEIPDB_API_KEY")
    if not TEAMS_WEBHOOK_URL:
        missing.append("TEAMS_WEBHOOK_URL")
    if not MONITOR_IP:
        missing.append("MONITOR_IP")

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Copy config.example.env to .env and fill in the values.")
        sys.exit(1)


def check_abuseipdb(ip: str) -> dict:
    """
    Query AbuseIPDB's /check endpoint in verbose mode.

    Returns the full API response data including the reports array,
    which contains per-report timestamps, comments, and category codes.
    """
    headers = {
        "Key": ABUSEIPDB_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "ipAddress": ip,
        "maxAgeInDays": MAX_AGE_DAYS,
        "verbose": "",
    }

    logger.info("Checking %s against AbuseIPDB (max age: %d days)...", ip, MAX_AGE_DAYS)

    try:
        response = requests.get(ABUSEIPDB_CHECK_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error("AbuseIPDB API request failed: %s", e)
        sys.exit(1)

    data = response.json().get("data", {})

    logger.info(
        "Result: score=%d/100, totalReports=%d, lastReportedAt=%s",
        data.get("abuseConfidenceScore", 0),
        data.get("totalReports", 0),
        data.get("lastReportedAt", "never"),
    )

    return data


def format_categories(category_ids: list) -> str:
    """Convert a list of AbuseIPDB category IDs to readable names."""
    names = [ABUSE_CATEGORIES.get(c, f"Unknown({c})") for c in category_ids]
    return ", ".join(names) if names else "N/A"


def build_alert_message(data: dict) -> str:
    """
    Build a Markdown-formatted alert message for Teams.

    Includes score, report count, latest report details, and direct
    links to AbuseIPDB history, takedown form, and MultiRBL deep-dive.
    """
    ip = data.get("ipAddress", MONITOR_IP)
    score = data.get("abuseConfidenceScore", 0)
    total_reports = data.get("totalReports", 0)
    last_reported = data.get("lastReportedAt", "N/A")

    # Extract most recent report details if available
    reports = data.get("reports", [])
    latest_comment = "N/A"
    latest_categories = "N/A"
    if reports:
        latest = reports[0]
        latest_comment = latest.get("comment", "No comment") or "No comment"
        latest_categories = format_categories(latest.get("categories", []))

    message = (
        f"**Breakout IP Flagged on AbuseIPDB** 🚨\n\n"
        f"**IP:** {ip}\n"
        f"**Score:** {score}/100\n"
        f"**Total Reports:** {total_reports}\n"
        f"**Last Reported:** {last_reported}\n"
        f"**Latest Category:** {latest_categories}\n"
        f"**Latest Comment:** {latest_comment}\n\n"
        f"**Next steps:**\n"
        f"- 🔍 [Full AbuseIPDB history](https://www.abuseipdb.com/check/{ip})\n"
        f"- 📝 [Takedown form](https://www.abuseipdb.com/takedown/{ip})\n"
        f"- 🌐 [Comprehensive blacklist check](https://multirbl.valli.org/lookup/{ip}.html)\n"
        f"- 🛡️ [Spamhaus check](https://check.spamhaus.org/results/?query={ip})"
    )

    return message


def send_teams_alert(message: str) -> bool:
    """
    Send the formatted alert to a Microsoft Teams channel via
    a Power Automate incoming webhook.

    The webhook expects a JSON body with a 'text' field. The Power Automate
    flow should be configured to extract triggerBody()?['text'] and post it
    to the target channel.
    """
    payload = {"text": message}

    logger.info("Sending alert to Teams...")

    try:
        response = requests.post(
            TEAMS_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Alert sent successfully (status %d).", response.status_code)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send Teams alert: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Breakout IP Blacklist Monitor")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check the score and print the alert, but don't send to Teams.",
    )
    args = parser.parse_args()

    validate_config()

    data = check_abuseipdb(MONITOR_IP)
    score = data.get("abuseConfidenceScore", 0)

    if score > SCORE_THRESHOLD:
        logger.warning(
            "Score %d exceeds threshold %d — generating alert.",
            score,
            SCORE_THRESHOLD,
        )
        message = build_alert_message(data)

        if args.dry_run:
            print("\n--- DRY RUN: Alert message (not sent) ---\n")
            print(message)
            print("\n--- End of alert ---\n")
        else:
            success = send_teams_alert(message)
            if not success:
                sys.exit(1)
    else:
        logger.info(
            "Score %d does not exceed threshold %d. No alert sent.",
            score,
            SCORE_THRESHOLD,
        )


if __name__ == "__main__":
    main()
