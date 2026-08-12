# Spamhaus DNSBL: Why Public Resolvers Don't Work

## Background

Spamhaus publishes its blocklists as DNS zones (DNSBLs). To check an IP, you reverse its octets, append the zone name, and do an A record lookup:

```
IP:       92.164.53.174
Reversed: 174.53.164.92
Query:    174.53.164.92.zen.spamhaus.org
```

The `zen.spamhaus.org` zone is a combined lookup covering SBL, CSS, XBL, and PBL in one query — Spamhaus explicitly recommends using ZEN rather than querying sub-zones separately.

## The Problem

Spamhaus blocks queries routed through public/open DNS resolvers (Google 8.8.8.8, Cloudflare 1.1.1.1, etc.). Instead of returning the real listing status, they return a special error code:

|Return Code|Meaning|
|-|-|
|`127.0.0.2`|Listed on SBL|
|`127.0.0.3`|Listed on PBL|
|`127.0.0.4`|Listed on XBL|
|`127.0.0.10`|Listed on XBL (other exploits)|
|`127.255.255.252`|Typo in DNSBL zone name|
|`127.255.255.254`|**Query via public/open resolver — blocked**|
|`127.255.255.255`|Excessive number of queries|
|NXDOMAIN|Not listed (clean)|

## What We Observed

```powershell
# Google's DNS-over-HTTPS — returned Status 3 (NXDOMAIN), appeared clean
Invoke-RestMethod -Uri "https://dns.google/resolve?name=174.53.164.92.zen.spamhaus.org\&type=A"
# Result: Status 3 — misleadingly suggests "not listed"

# Cloudflare's resolver — returned the actual block code
Resolve-DnsName -Name "174.53.164.92.zen.spamhaus.org" -Type A -Server 1.1.1.1
# Result: 127.255.255.254 — "query via public resolver"

# Meanwhile, Spamhaus's own web checker showed a real XBL listing
# https://check.spamhaus.org/results/?query=92.164.53.174
```

The IP was genuinely listed on XBL, but neither public resolver returned a real answer. Google's resolver returned a cached/synthetic NXDOMAIN (appearing clean when it wasn't), while Cloudflare at least returned the explicit block code.

## Why This Happens

Spamhaus's public DNSBL mirrors are a free service with fair-use restrictions. Open/public resolvers aggregate queries from millions of users, making it impossible for Spamhaus to identify or rate-limit individual queriers. Their policy is to block these resolvers entirely rather than risk abuse of their free tier.

## Implications for Automation

DNS-over-HTTPS (via Google or Cloudflare) cannot be used for reliable Spamhaus checks. The options are:

1. **Spamhaus Data Query Service (DQS)** — paid/registered access with proper attribution, not subject to public resolver blocking.
2. **Direct DNS query from your own infrastructure** — using your network's own DNS resolver (not a public one), which Spamhaus can attribute and rate-limit properly.
3. **Manual checks only** — use `check.spamhaus.org` as a human-operated reference link in alerts, which is the approach this project takes.

## Note for Other DNSBLs

This restriction is specific to Spamhaus. Other DNSBLs (SpamRATS, HostKarma, Barracuda) do not block public resolvers the same way, so DNS-over-HTTPS works fine for those.

