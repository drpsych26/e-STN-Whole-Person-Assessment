# STN lowest-cost Microsoft identity, email and Azure account setup

**Decision:** Start with a company-owned Microsoft Entra tenant and Azure free account. Do not purchase Microsoft 365 licences yet. This is an account-establishment and learning phase, not a production hosting budget.

## Domain already held by STN

Use the existing STN domain, `supportivetherapy.network`, rather than purchasing another domain. Keep its registration at the current registrar. Do not change nameservers or existing website records as part of this setup.

## Step 1 — Establish the Microsoft tenant

1. Open https://azure.microsoft.com/en-nz/pricing/purchase-options/azure-account/
2. Select **Try Azure for free** if STN is eligible as a new Azure customer.
3. Register using an STN-controlled administrator contact and STN's legal business details.
4. Complete Microsoft's identity and payment-card verification. A temporary card authorisation may be used for verification.
5. Create the Microsoft Entra tenant for STN. Use an initial `stnlimited.onmicrosoft.com` tenant domain if prompted; the exact tenant prefix must be available.
6. Create individually named admin accounts; enable MFA immediately. Keep at least two controlled emergency admin identities and secure recovery details.
7. Add `supportivetherapy.network` as a custom domain in Microsoft Entra admin center and verify ownership using the TXT record Microsoft supplies. Add only that TXT record at the registrar. Do not alter MX, SPF, DKIM, DMARC, A, or CNAME records during tenant verification.
8. Record the tenant ID, verified domain, account owner and recovery process in STN's restricted asset register.

## Step 2 — Understand the free Azure account

Microsoft's current Azure Free Account offer is for eligible new Azure customers and includes a USD $200 credit for 30 days, selected services free for 12 months, and selected always-free services. It is intended for exploration and proof-of-concept. To continue beyond the credit period or 30 days, the account must be moved to pay-as-you-go. Do not assume a production clinical platform can run indefinitely for free.

Official details: https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account/

**Important:** Do not provision the production database, production App Service, backups, private endpoints, monitoring ingestion or other chargeable production services while relying on the temporary credit. The free account does not constitute a funded production subscription or a production cost guarantee.

## Step 3 — Email decision

The domain-based mailbox is not required to create the Entra tenant. Start with the tenant's `onmicrosoft.com` admin identity and a separately controlled recovery contact.

Options:
- **Lowest immediate spend:** defer custom-domain mailboxes. Cloudflare Email Routing can forward incoming mail for free, but it is forwarding, not a full mailbox and does not by itself provide outbound SMTP sending. It also requires Cloudflare DNS configuration; do not move STN's DNS until website and existing mail records are inventoried.
- **Free hosted mailbox possibility:** Zoho advertises a free custom-domain plan for up to five users/5 GB each, but its own documentation says availability is limited to selected data centres (US, EU and India) and features are restricted. Do not use it for clinical or sensitive correspondence without privacy, residency, security and service-availability review.
- **Straightforward Microsoft mailbox:** Microsoft 365 Business Basic (no Teams) is currently listed in NZ at NZ$8.70 per user/month on annual billing, excluding tax. It includes custom-domain email and web/mobile Office apps. Buy only when STN approves recurring spend.

Microsoft pricing: https://www.microsoft.com/en-nz/microsoft-365/business/no-teams-plans-and-pricing  
Cloudflare Email Routing: https://developers.cloudflare.com/email-routing/  
Zoho free plan limitations: https://www.zoho.com/mail/compare/overview.html

For an organisation handling mental-health information, do not route clinical records, referrals, crisis details or identifiable client information through an unassessed free email provider or personal mailbox. Email should not become the clinical record system.

## Step 4 — Production boundary

Keep the Azure tenant company-owned from day one. Use the free account only to establish the tenant, learn the portal and prepare configuration. Before creating chargeable production resources:
- Approve a written monthly operating budget.
- Confirm Azure region and service/SKU availability.
- Complete NZ privacy impact and cross-border data-flow assessments.
- Confirm contracts, retention, backups, restore and incident response.
- Configure MFA, least privilege, monitoring, security and audit.
- Complete clinical validation and release approval.

Azure budgets generate alerts; they are not hard spending caps. Do not rely on them alone to prevent charges.

## What ChatGPT cannot do on STN's behalf

The STN account owner must complete Microsoft's identity verification, accept Microsoft's terms, enter payment details and approve any subscription conversion or charge. Do not send passwords, MFA codes, payment-card details, recovery codes, private keys or access tokens in chat.