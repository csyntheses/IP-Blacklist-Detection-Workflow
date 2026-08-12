# AbuseIPDB Takedown Request Template

Use this template when submitting a takedown request at `https://www.abuseipdb.com/takedown/{IP}` after your analyst has reviewed the reports and confirmed the underlying issue has been addressed.

## Template (FTTH/ISP Shared Breakout IP)

> This IP address ({IP}) is a shared breakout/NAT IP used for outbound traffic from our FTTH (Fiber-to-the-Home) residential customer base. As with most carrier-grade NAT deployments, multiple subscriber connections share this public IP, so reported activity may originate from a single customer device rather than reflecting the broader network.
>
> We've reviewed our records for the reported timeframe and [choose the applicable line]:
>
> - identified the subscriber session associated with this activity and have taken action (e.g., customer notification, service suspension, or device remediation guidance) as of [date].
> - found no internal record of the reported behavior correlating to a specific subscriber; this may reflect a resolved issue, a since-reassigned dynamic session, or a false positive.
>
> As an ISP, we operate abuse-handling procedures for reports on this IP range and take subscriber-level action when a specific device or account is identified as the source. We'd appreciate the listing being reviewed in light of the shared/NAT nature of this address, and are happy to provide additional network context if useful.

## Tips

- **Be honest, not defensive** — if there genuinely was an incident, say so and describe the fix. Reviewers trust "yes, this happened, here's what we did" far more than blanket denial.
- **Include dates** if you know when the underlying issue was fixed — helps establish that reports predate remediation.
- **If it's a cloud/hosting IP**, mention if you recently acquired it — previous tenants' bad behavior is a common and usually accepted explanation.
- **Don't over-promise** — avoid absolute claims like "this will never happen again"; stick to what controls you actually have in place.

## Note on AbuseIPDB's `clear-address` API

The `/api/v2/clear-address` endpoint only deletes reports that *your own account* submitted. It cannot remove reports filed by other users. For disputing other users' reports, the takedown request form (linked above) is the correct path.
