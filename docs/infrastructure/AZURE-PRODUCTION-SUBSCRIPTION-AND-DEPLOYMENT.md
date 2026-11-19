# STN Azure production subscription — setup and deployment requirements

**Target:** Supportive Therapy Network Limited  
**Environment:** Production (not development or staging)  
**Primary Azure region:** New Zealand North (Auckland), region code `newzealandnorth`  
**Status:** Production design and account setup instructions. No Azure subscription or resources have been created by this repository change. Do not process identifiable client information until the production go-live gate is signed.

## 1. Subscription ownership and account

The Azure tenant, billing account, subscription and all production resources must be owned and controlled by Supportive Therapy Network Limited, not a developer's personal account.

Before creating the subscription, STN must have:
- A company-controlled Microsoft Entra tenant and at least two individually named emergency/global administrators protected by MFA.
- A company-controlled billing account/payment method and authorised billing contact.
- A named subscription owner and a separate billing administrator.
- Recovery methods and emergency-access accounts stored under documented organisational control.
- A dedicated production subscription. Do not mix production with personal, test, sandbox or unrelated business workloads.
- A documented subscription naming convention, resource naming convention, cost centre and owner.

Suggested names (confirm uniqueness at creation):
- Subscription display name: `STN-Clinical-Production`
- Resource group: `rg-stn-clinical-prod-nzn`
- Region: `New Zealand North`
- Resource tags: `organisation=STN`, `environment=production`, `data-classification=health-information`, `owner=STN`, `managed-by=terraform`.

Do not create the subscription under a personal Microsoft account if STN can establish a company tenant first. The person creating a subscription generally receives Owner permissions; grant access deliberately using Azure RBAC. Avoid shared administrator logins.

## 2. Create the Azure subscription

1. Go to https://portal.azure.com and sign in using the STN-controlled Microsoft work account.
2. Open **Subscriptions** → **Add** (or the applicable billing scope → **Subscriptions** → **Add**).
3. Select the appropriate Azure offer/billing scope available to STN. For a new small business, compare pay-as-you-go with a Microsoft Customer Agreement / Azure plan through Microsoft's sales channel if needed.
4. Set subscription name to `STN-Clinical-Production`.
5. Select the STN company billing profile and authorised payment method. Confirm GST/tax invoice details with STN's accountant.
6. Create the subscription and record the subscription ID in STN's restricted secrets/asset register. Do not put subscription IDs in public source code if avoidable; never put credentials or secrets in Git.
7. Confirm the subscription appears under the STN tenant and the billing owner can view invoices and usage.
8. Assign named administrators using least privilege. Use Owner only for the minimum number of accountable subscription administrators; use Contributor and narrowly scoped roles for operators. Assign role eligibility through Privileged Identity Management where the tenant/licensing supports it.
9. Create a production budget and alert thresholds before provisioning resources. Budget alerts are notifications, not hard spending caps. Review actual usage and set Azure Policy/automation controls separately.

Microsoft references:
- Azure portal: https://portal.azure.com
- Create a Microsoft Customer Agreement subscription: https://learn.microsoft.com/azure/cost-management-billing/manage/create-subscription-request
- Subscription administrator roles: https://learn.microsoft.com/azure/billing-add-change-azure-subscription-administrator
- Billing access: https://learn.microsoft.com/azure/cost-management-billing/manage/manage-billing-access
- Azure pricing calculator: https://azure.microsoft.com/pricing/calculator/

## 3. Recommended production architecture

### Application/API
- Azure App Service for Linux hosting a pinned, signed STN FastAPI container.
- HTTPS only; TLS 1.2 minimum (prefer TLS 1.3 where supported).
- Managed identity for Azure resource access.
- Private networking to data services; public ingress only through an approved edge/WAF design.
- Health endpoints must not disclose configuration, dependencies or secrets.
- Separate production deployment slot or controlled blue/green deployment and tested rollback.

### Database
- Azure Database for PostgreSQL Flexible Server, production General Purpose or Memory Optimized SKU selected after capacity and cost modelling.
- New Zealand North primary region, private access only, no public network access.
- Zone-redundant high availability if the selected SKU/configuration is supported and provisioned in-region.
- Encryption at rest and TLS in transit; least-privilege database roles.
- Automated backups with retention set to the approved retention schedule; test point-in-time restore and full recovery.
- Database schema migrations reviewed, versioned and reversible where possible.
- No clinical records in browser localStorage or as the system of record on a mobile device.

### Identity
- Microsoft Entra workforce tenant for STN staff, individual accounts, MFA and Conditional Access.
- OIDC access tokens validated by the API (issuer, audience, signature, expiry, not-before).
- Server-side role and organisation/client record scoping; deny by default.
- No shared clinician accounts. Account lifecycle, leaver revocation, recovery and periodic access reviews are mandatory.
- Entra identity processing location must be documented separately from database residency. Do not claim all identity data is stored in New Zealand.

### Secrets, audit and monitoring
- Azure Key Vault with RBAC, purge protection, soft delete and private endpoint; secrets referenced by managed identity, not embedded in app settings or source.
- Append-only/tamper-evident audit events for access, creation, edits, exports, finalisation, amendments, role changes and administrative actions.
- Send operational/security logs to Azure Monitor / Log Analytics / Application Insights with sensitive payloads, clinical answers, tokens and unnecessary identifiers excluded.
- Alert on anomalous sign-ins, privilege changes, access failures, unusual exports, service availability and security events.
- Restrict audit access and protect retention against administrator tampering.

### Network and edge
- Virtual Network, private PostgreSQL access, private endpoints for Key Vault and registry, DNS zones, network security groups and outbound restrictions.
- WAF/edge service only after regional availability, data processing, logging location and cost are verified. Do not assume Azure Front Door/WAF processing or logs remain in New Zealand.
- No public database endpoint. Restrict management plane to approved administrators and secure admin workstations.

## 4. New Zealand residency and disaster recovery decision

Microsoft lists New Zealand North in Auckland and shows three availability zones. PostgreSQL Flexible Server's current regional availability table lists New Zealand North, but the service feature matrix must be checked for the exact selected SKU and high-availability option at deployment time.

New Zealand North is listed as a non-paired region. Do not assume native geo-redundant backups or an in-country paired region. A production disaster-recovery design must explicitly decide:
- Whether recovery copies must remain in New Zealand.
- Whether a second NZ region/service is available and suitable.
- Whether cross-border replication is legally and contractually acceptable.
- RPO/RTO, restore ownership, test frequency and continuity procedures.

No cross-border replication or overseas backup location may be enabled until STN's privacy officer and qualified NZ legal adviser approve the data-flow and contractual basis. A local primary database does not by itself establish that all service metadata, identity, support or telemetry stays in NZ.

## 5. Security and compliance controls required before data

- Approved privacy impact assessment and data-flow map.
- Data processor/subprocessor agreements and documented hosting/support locations.
- Threat model and independent penetration test with critical/high findings remediated.
- Entra MFA, least privilege, role scoping and access-review evidence.
- Database encryption, private networking, Key Vault and secret rotation.
- Immutable/tamper-evident audit controls and monitoring.
- Backup restore, disaster recovery and incident response exercises.
- Approved consent/privacy notice, access/correction, retention and secure disposal workflows.
- Instrument permissions and digital reproduction/scoring/reporting rights.
- Clinical validation, clinician scope and signed clinical governance approval for the exact app version.
- Human crisis escalation with named accountable operator, staffed coverage, acknowledgement timeout, fallback and documented SOP.
- Signed release approval and controlled change/rollback plan.

## 6. Cost controls

Before deployment:
1. Build an Azure Pricing Calculator estimate using New Zealand North and the intended App Service plan, PostgreSQL SKU/storage/HA, Key Vault, private endpoints, monitoring, backups, WAF/edge and outbound traffic.
2. Obtain STN budget owner approval for monthly run-rate and one-off setup costs.
3. Create a subscription budget with alerts at 50%, 75%, 90% and 100% of the approved monthly amount.
4. Review log ingestion and retention costs; avoid collecting clinical payloads.
5. Reassess cost and capacity monthly during the first 90 days.

The calculator is an estimate; actual consumption varies. Do not use low-cost development SKUs for production clinical data simply to reduce initial cost.

## 7. Production deployment sequence

1. STN creates and verifies the company-owned Azure tenant and subscription.
2. STN records subscription ID and grants narrowly scoped access to named deployment identities.
3. Create private Terraform state storage with encryption, versioning, soft delete and access restrictions.
4. Review Terraform plan and security/network architecture with STN's accountable infrastructure owner.
5. Deploy production resource group, VNet, private DNS, Key Vault, PostgreSQL, App Service, registry, monitoring and backup policy.
6. Configure OIDC, MFA, server-side RBAC and organisation/client scoping.
7. Implement and test persistent assessment records, consent workflow and immutable audit.
8. Complete privacy/security review, penetration test, restore drill, clinical validation, UAT and operational readiness.
9. Deploy the signed production app and API using controlled CI/CD with workload identity federation; no long-lived client secrets in GitHub.
10. Obtain written go/no-go approval for the exact release. Only then permit identifiable client data.

## 8. Credentials and access

The subscription owner must create the Azure subscription and use the Azure portal to grant deployment access. Never send passwords, MFA codes, private keys, keystores, connection strings or access tokens through ChatGPT, email or GitHub issues. Use workload identity federation for GitHub Actions and managed identity inside Azure.

This document does not create an Azure subscription, accept Microsoft terms, authorise expenditure, provision resources, or certify STN's clinical system.