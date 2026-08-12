# Shuffle SOAR Workflow: Breakout IP - AbuseIPDB Monitor

This project was also implemented as a no-code workflow in [Shuffle](https://shuffler.io), an open-source SOAR platform. This document describes the workflow structure and configuration for anyone wanting to reproduce it in Shuffle rather than (or alongside) the standalone Python script.

## Workflow Nodes

```
┌──────────────┐     ┌─────────────────────────┐     ┌──────────────────┐
│  Scheduler   │────▶│  Pull Abuse IPDB Records │────▶│  Post to Teams   │
│  (every 6h)  │     │  (HTTP GET)              │     │  (HTTP POST)     │
└──────────────┘     └─────────────────────────┘     └──────────────────┘
                                                           │
                                                      1 condition:
                                                      score > 27
```

## Node 1: Scheduler

- **Type:** Trigger — Scheduler
- **Cron:** `0 */6 * * *` (every 6 hours)

## Node 2: Pull Abuse IPDB Records

- **Type:** HTTP (GET)
- **URL:** `https://api.abuseipdb.com/api/v2/check?ipAddress=<YOUR_IP>&maxAgeInDays=90&verbose`
- **Headers:**
  - `Key: <YOUR_ABUSEIPDB_API_KEY>`
  - `Accept: application/json`

## Node 3: Post to Teams (HTTP POST)

- **Type:** HTTP (POST)
- **URL:** Your Power Automate webhook URL
- **Headers:**
  - `Content-Type: application/json`
- **Body:**
```json
{
  "text": "**Breakout IP Flagged on AbuseIPDB** 🚨\n\n**IP:** <IP>\n**Score:** $pull_abuse_ipdb_records.body.data.abuseConfidenceScore/100\n**Total Reports:** $pull_abuse_ipdb_records.body.data.totalReports\n**Last Reported:** $pull_abuse_ipdb_records.body.data.lastReportedAt\n\n**Next steps:**\n- 🔍 [Full AbuseIPDB history](https://www.abuseipdb.com/check/<IP>)\n- 📝 [Takedown form](https://www.abuseipdb.com/takedown/<IP>)\n- 🌐 [Comprehensive blacklist check](https://multirbl.valli.org/lookup/<IP>.html)"
}
```

## Condition: Score Threshold

Applied on the connecting line between Node 2 and Node 3:

- **Source:** `$pull_abuse_ipdb_records.body.data.abuseConfidenceScore`
- **Operator:** `larger than`
- **Destination:** `27` (static value — adjust to your baseline)

## Power Automate Configuration

The Teams webhook is set up via Power Automate Workflows:

1. **Trigger:** "When a Teams webhook request is received"
2. **Action:** "Post message in a chat or channel"
   - **Post as:** Flow bot
   - **Post in:** Group chat (or Channel)
   - **Message:** Use the expression `triggerBody()?['text']` to extract the message content from the incoming webhook body.

## Known Issues Encountered During Build

| Issue | Root Cause | Resolution |
|-------|-----------|------------|
| `illegal_argument_exception: alias [workflowapp]` | Shuffle backend Elasticsearch index conflict | Transient platform issue — resolved by deleting and recreating the node |
| `MISE unauthorized` (401) | Browser autofill injected stray username/password values into the HTTP node | Cleared the username and password fields; disabled browser autofill for shuffler.io |
| Shuffle Datastore node hanging indefinitely | Platform instability | Dropped the de-dupe feature; implemented threshold-only alerting |
| `ConnectionError: Failed to resolve` | DNS resolution failure on Shuffle's infrastructure | Transient — resolved on retry |

## Potential Enhancements

- **De-duplication via Datastore:** Use Shuffle's built-in Datastore (Get/Set actions) to remember `lastReportedAt` and only alert when a genuinely new report appears. Dropped from this build due to Datastore reliability issues, but the logic is straightforward — see the README for the intended flow.
- **Additional DNSBL checks:** SpamRATS, HostKarma, and Barracuda can be checked via DNS-over-HTTPS (unlike Spamhaus, they don't block public resolvers). Add parallel HTTP GET nodes querying `dns.google/resolve?name=<reversed_ip>.<zone>&type=A` for each.
