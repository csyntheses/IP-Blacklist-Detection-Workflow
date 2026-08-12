# test_abuseipdb.ps1
# Quick PowerShell scripts used during development to validate API endpoints
# before wiring them into the automation pipeline.

# --- Test 1: Basic AbuseIPDB check -------------------------------------------
# Confirms API key works and returns score/report data.

$headers = @{
    "Key"    = "YOUR_API_KEY_HERE"
    "Accept" = "application/json"
}

Invoke-RestMethod `
    -Uri "https://api.abuseipdb.com/api/v2/check?ipAddress=92.164.53.174&maxAgeInDays=90&verbose" `
    -Headers $headers `
    -Method Get

# --- Test 2: Verbose output with reports array expanded ----------------------
# PowerShell truncates nested objects by default. This expands the reports array
# so you can see actual timestamps, comments, and category codes.

Invoke-RestMethod `
    -Uri "https://api.abuseipdb.com/api/v2/check?ipAddress=92.164.53.174&maxAgeInDays=90&verbose" `
    -Headers $headers `
    -Method Get `
    | Select-Object -ExpandProperty data `
    | Select-Object -ExpandProperty reports `
    | Format-List

# --- Test 3: Teams webhook (Power Automate) ----------------------------------
# Confirms the Power Automate webhook accepts JSON and posts to the Teams channel.
# Note: the Power Automate flow's "Post message" step must use the expression
# triggerBody()?['text'] to extract the message from the incoming request body.

$body = @{ text = "Test alert from PowerShell" } | ConvertTo-Json
Invoke-RestMethod `
    -Uri "YOUR_POWER_AUTOMATE_WEBHOOK_URL_HERE" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

# --- Test 4: Spamhaus DNSBL via DNS-over-HTTPS (Google) ----------------------
# Note: This returns Status 3 (NXDOMAIN) even for listed IPs because Google's
# public resolver is blocked by Spamhaus (returns 127.255.255.254).
# See docs/spamhaus-dnsbl-notes.md for the full explanation.

Invoke-RestMethod -Uri "https://dns.google/resolve?name=174.53.164.92.zen.spamhaus.org&type=A"

# --- Test 5: Spamhaus via Cloudflare resolver (also blocked) -----------------
# Returns 127.255.255.254 — Spamhaus's error code for "query via public resolver."
# This is NOT a listing result; it means the query itself was rejected.

Resolve-DnsName -Name "174.35.164.102.zen.spamhaus.org" -Type A -Server 1.1.1.1
