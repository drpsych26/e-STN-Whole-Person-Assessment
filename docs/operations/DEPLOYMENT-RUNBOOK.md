# STN API — deployment runbook (staging)

**Status: draft procedure; nothing has been deployed.** This runbook covers the deploy kit in this repository: the API container (`backend/Dockerfile`), the Bicep templates (`infra/azure/`) and the manual workflow `.github/workflows/deploy-staging.yml`. Staging holds **synthetic data only**. Nothing here is evidence that a production environment exists or meets a release gate; those stay in `docs/release/PRODUCTION-GO-LIVE-GATE.md`. Hosting requirements come from `docs/infrastructure/AZURE-PRODUCTION-SUBSCRIPTION-AND-DEPLOYMENT.md`; backup and restore from `docs/operations/BACKUP-AND-RESTORE-RUNBOOK.md`.

Never put passwords, keys, tokens, connection strings or MFA codes in GitHub, chat or email. The deploy workflow uses workload identity federation (no client secret), the API uses managed identities, and the database accepts Microsoft Entra authentication only.

## 1. What the kit builds

| Component | Resource (staging names; `<sfx>` is a stable 8-character suffix) | Notes |
|---|---|---|
| API | App Service for Linux plan `asp-stn-stg-nzn`, web app `app-stn-api-stg-<sfx>` | Custom container `stn-api:<tag>`, HTTPS only, TLS 1.2+, FTP and basic publishing credentials off, VNet integration with all outbound traffic routed through the VNet, image pulled over the VNet with the API's managed identity |
| Migrations | Slot `migrate` on the same app | Runs the same image with `STN_PROCESS_ROLE=migrate`: applies migrations, creates the API's database principal, grants it data privileges only, then serves `/healthz` and `/readyz` only. Never swapped; stopped after every deploy |
| Identities | `id-stn-api-stg`, `id-stn-migrate-stg` (user-assigned) | API: AcrPull, Key Vault Secrets User, database DML. Migrate: AcrPull, PostgreSQL Entra administrator |
| Database | PostgreSQL Flexible Server 16 `pg-stn-stg-<sfx>`, database `stn` | VNet-injected (private access only), Entra authentication only (password authentication disabled), `require_secure_connection` on, backups 7 days (production template 35), geo-redundant backup **Disabled**, HA parameter |
| Keys and secrets | Key Vault `kv-stn-stg-<sfx>` | RBAC, soft delete 90 days, purge protection, public network access disabled, private endpoint. Holds the data-encryption keys (added by you, section 6) and the Redis URL (written by the deployment) |
| Rate-limit store | Azure Managed Redis `redis-stn-stg-<sfx>` (Balanced B0) | TLS only, public access disabled, private endpoint, URL in Key Vault, referenced by the API |
| Registry | Container registry `acrstnstg<sfx>` (Premium) | Admin user and anonymous pull off; private endpoint for the app's pulls. Public network access stays **enabled** in staging so GitHub-hosted runners can push |
| Network | VNet `vnet-stn-stg-nzn` 10.60.0.0/16; subnets for the app, PostgreSQL and private endpoints; NSGs; private DNS zones for Key Vault, registry, Redis and PostgreSQL | No public database, vault or cache endpoint |
| Monitoring | Log Analytics `log-stn-stg-nzn` (90 days) | Diagnostic settings on the app, slot, database, Key Vault and registry |

Every resource carries the tags `organisation=STN`, `environment`, `data-classification=health-information`, `owner=STN`, `managed-by=bicep`.

**Where the kit departs from the infrastructure document** (for the infrastructure owner to accept or change):

1. **Bicep, not Terraform.** The infrastructure document plans Terraform with private state storage. Bicep keeps state in Azure Resource Manager, so no state storage account is needed; the tag is `managed-by=bicep`.
2. **Registry public access in staging.** The document asks for a private endpoint for the registry. The endpoint exists and the app pulls through it, but public access stays enabled because GitHub-hosted runners push from the internet. Before production, push from a runner inside the network and set `registryPublicNetworkAccess = 'Disabled'`.
3. **Azure Managed Redis**, not Azure Cache for Redis. Microsoft has announced retirement of Azure Cache for Redis tiers; Azure Managed Redis is its replacement.
4. **Migrations in an App Service slot.** Container Apps jobs and Container Instances were not available in New Zealand North when this was written, so migrations run in a dedicated `migrate` slot that is never swapped.
5. **No WAF or edge service.** The document makes this conditional on regional availability and data-processing review. The API is reached on its App Service hostname (optionally restricted by `allowedInboundCidrs`).
6. **Image signing** is not implemented (the document asks for a signed container). Images are tagged with the commit, built from a digest-pinned base, scanned by Trivy in CI, and labelled with the commit SHA.

## 2. Azure subscription and resource group (owner)

1. Use a company-owned subscription. A separate staging subscription (for example `STN-Clinical-Staging`) is preferred; at minimum use a separate resource group. Do not use the production subscription for staging experiments.
2. Create the resource group in New Zealand North:
   ```sh
   az group create --name rg-stn-clinical-stg-nzn --location newzealandnorth \
     --tags organisation=STN environment=staging data-classification=health-information owner=STN managed-by=bicep
   ```
3. Register the resource providers once per subscription:
   ```sh
   for ns in Microsoft.Web Microsoft.DBforPostgreSQL Microsoft.KeyVault Microsoft.ContainerRegistry \
             Microsoft.Cache Microsoft.Network Microsoft.OperationalInsights Microsoft.Insights Microsoft.ManagedIdentity; do
     az provider register --namespace "$ns"
   done
   ```
4. Check in the portal that these are offered in New Zealand North for the subscription: App Service plan `P0v3`, PostgreSQL Flexible Server `Standard_B1ms`, Azure Managed Redis `Balanced_B0`, and Premium container registry. If one is not offered, change it in `infra/azure/staging.bicepparam` through a pull request.
5. Create a budget with alerts on the subscription or resource group before the first deploy (section 13).

## 3. Deployment identity (owner)

The workflow signs in as an Entra application through a federated credential that trusts only this repository's `staging` environment.

```sh
SUB=<subscription-id>  RG=rg-stn-clinical-stg-nzn
APP_ID=$(az ad app create --display-name "STN GitHub deploy (staging)" --query appId -o tsv)
SP_OBJECT_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
cat > fic.json <<'EOF'
{
  "name": "github-staging",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:drpsych26/e-STN-Whole-Person-Assessment:environment:staging",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF
az ad app federated-credential create --id "$APP_ID" --parameters fic.json
echo "AZURE_CLIENT_ID=$APP_ID  AZURE_DEPLOY_PRINCIPAL_OBJECT_ID=$SP_OBJECT_ID"
```

Create no client secret or certificate for this application.

Role assignments, scoped to the staging resource group only:

```sh
SCOPE="/subscriptions/$SUB/resourceGroups/$RG"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal \
  --role Contributor --scope "$SCOPE"

# The templates assign AcrPull, AcrPush and Key Vault Secrets User. Allow the deploy identity to
# assign those three roles and nothing else.
ROLES="7f951dda-4ed3-4680-a7ca-43fe172d538d, 8311e382-0749-4cb8-b61a-304f252e45ec, 4633458b-17de-408a-b874-0445c86b69e6"
COND="((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ROLES})) AND ((!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})) OR (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ROLES}))"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal \
  --role "Role Based Access Control Administrator" --scope "$SCOPE" \
  --condition "$COND" --condition-version "2.0"
```

The role definition ids are AcrPull, AcrPush and Key Vault Secrets User. If you prefer not to delegate role assignment, give the deploy identity Contributor only, leave `AZURE_DEPLOY_PRINCIPAL_OBJECT_ID` unset, and create the three kinds of assignment yourself after the first foundation run (the deployment will fail on them until you do).

## 4. GitHub environment and variables (owner)

1. Repository **Settings → Environments → New environment** `staging`.
2. **Required reviewers:** yourself (and a second person when available). **Deployment branches:** `main` only. Do not allow administrators to bypass.
3. Add these **environment variables** (not secrets; none of them is a credential):

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | Application (client) id from section 3 |
| `AZURE_TENANT_ID` | STN tenant id |
| `AZURE_SUBSCRIPTION_ID` | Staging subscription id |
| `AZURE_RESOURCE_GROUP` | `rg-stn-clinical-stg-nzn` |
| `AZURE_DEPLOY_PRINCIPAL_OBJECT_ID` | Service principal object id from section 3 (gets AcrPush). Optional, see section 3 |
| `STN_OIDC_ISSUER`, `STN_OIDC_AUDIENCE`, `STN_OIDC_JWKS_URL`, `STN_OIDC_ROLE_MAP`, `STN_OIDC_ORG_CLAIM`, `STN_MFA_ACRS_VALUES` | From section 5 |
| `STN_BOOTSTRAP_ADMIN_ORG`, `STN_BOOTSTRAP_ADMIN_SUBJECT` | From section 7 step 4 |

If any of the first four is missing the workflow stops at its preflight step with an error naming the missing variables, before it signs in, and changes nothing.

The repository is currently public, so workflow logs are public and Azure CLI output may show the subscription and tenant ids. Microsoft does not treat these ids as secrets, but the infrastructure document asks that they stay out of public view where possible. Deciding the repository's visibility (go-live gate owner action 11) before the first deploy avoids this.

## 5. Identity provider for the API (owner)

1. In the STN tenant, register an application **STN API (staging)**. Under **Expose an API**, set the Application ID URI (for example `api://stn-api-staging`) and add a scope for the app.
2. Under **App roles**, create `STN.Clinician`, `STN.Reviewer` and `STN.Admin` (member type Users/Groups). Assign test accounts to them; synthetic test accounts only.
3. In the manifest set `"requestedAccessTokenVersion": 2`, so tokens are issued by the v2.0 endpoint.
4. Require MFA with Conditional Access and an authentication context (for example `c1`) mapped to the API. Conditional Access needs an Entra ID licence that includes it (a cost to check).
5. Set the GitHub variables:
   - `STN_OIDC_ISSUER` = `https://login.microsoftonline.com/<tenant-id>/v2.0`
   - `STN_OIDC_AUDIENCE` = the API application's client id (v2.0 access tokens carry the client id as `aud`)
   - `STN_OIDC_JWKS_URL` = `https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys`
   - `STN_OIDC_ROLE_MAP` = `STN.Clinician=clinician,STN.Reviewer=reviewer,STN.Admin=admin`
   - `STN_OIDC_ORG_CLAIM` = `tid` (one organisation per tenant) or the custom claim decided under go-live owner action 13
   - `STN_MFA_ACRS_VALUES` = the authentication context id, for example `c1`

Without the issuer and audience the API refuses every sign-in (503); the workflow warns about this.

## 6. Data-encryption key in Key Vault (owner, after the foundation run)

The vault has public access disabled and its firewall bypass off, so adding the key needs a short, deliberate window. The next deployment closes it again.

```sh
KV=<keyVaultName from the foundation run summary or: az keyvault list -g $RG --query [0].name -o tsv>
MY_IP=$(curl -fsS https://api.ipify.org)
ME=$(az ad signed-in-user show --query id -o tsv)
KV_ID=$(az keyvault show --name "$KV" --query id -o tsv)

az keyvault update --name "$KV" --public-network-access Enabled --default-action Deny
az keyvault network-rule add --name "$KV" --ip-address "$MY_IP/32"
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Key Vault Secrets Officer" --scope "$KV_ID"
# allow a few minutes for the role assignment to take effect

umask 077
python3 -c "import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),end='')" > stn-data-key-1.txt
az keyvault secret set --vault-name "$KV" --name stn-data-key-1 --file stn-data-key-1.txt \
  --content-type stn-data-key -o none
# Escrow: copy stn-data-key-1.txt to STN's offline key escrow (backup runbook section 2), then:
shred -u stn-data-key-1.txt

az role assignment delete --assignee "$ME" --role "Key Vault Secrets Officer" --scope "$KV_ID"
az keyvault network-rule remove --name "$KV" --ip-address "$MY_IP/32"
az keyvault update --name "$KV" --public-network-access Disabled
```

The secret name is the key id. It must match `dataKeySecretNames` and `activeDataKeyId` in `infra/azure/staging.bicepparam` (default `stn-data-key-1`). Staging keys must never be reused in production.

## 7. First deploy

1. Complete sections 2–5.
2. **Actions → Deploy staging (manual) → Run workflow** on `main`, phase **foundation**. Approve the environment when asked. This creates everything except the App Service.
3. Add the data key (section 6).
4. **First admin.** The account registry is required in staging (`STN_ACCOUNT_REGISTRY_REQUIRED=true`), so the first admin must be registered before anyone can use the API. There is no operator shell inside the staging network, so the migrate slot does it: set `STN_BOOTSTRAP_ADMIN_ORG` (the organisation value the token will carry, for example the tenant id when the org claim is `tid`) and `STN_BOOTSTRAP_ADMIN_SUBJECT` (the `sub` claim of that admin's access token for the STN API). `sub` in Entra access tokens is specific to the application, so read it from a real access token for the STN API and decode it locally, never on a website:
   ```sh
   python3 -c "import sys,json,base64;p=sys.argv[1].split('.')[1];print(json.loads(base64.urlsafe_b64decode(p+'='*(-len(p)%4)))['sub'])" "<access-token>"
   ```
   The migrate step registers and activates that subject only if it has never been registered; an existing account is never changed, so a suspended or deactivated account is not reactivated. Both steps are audited (actor `operator:cli`, reason `deploy_bootstrap`). You can remove the two variables after the first successful run.
5. Run the workflow again with phase **full**. It checks the data key exists (metadata only), builds and pushes `stn-api:<commit>`, runs the migrate slot until `/readyz` reports the new build, moves the API to the new image, and smoke-tests `/healthz` and `/readyz`. The run summary shows the API hostname.
6. Check:
   ```sh
   curl -fsS https://<api-host>/healthz   # {"status":"alive","build":"<commit12>"}
   curl -fsS https://<api-host>/readyz    # {"status":"ready","build":"<commit12>"}
   curl -s -o /dev/null -w '%{http_code}\n' https://<api-host>/v1/me   # 401 without a token
   ```
7. Record the run URL, image tag and checks in the release evidence (go-live gate). A green staging deploy does not tick a gate.

**Readiness semantics.** `/healthz` is liveness only (App Service's health check). `/readyz` reports ready only when the database schema exactly matches the build, the active data key is available and the shared rate-limit store answers; it fails closed and never shows which check failed (the API logs the check name). Between the migration and the API switch the old API reports not ready, because the schema is ahead of its build; staging accepts that short window.

## 8. DNS for the API subdomain (owner, optional)

The API works on its App Service hostname. To use, for example, `api.supportivetherapy.network`:

1. Get the values: `az webapp show -g $RG -n <app> --query "{host:defaultHostName, verification:customDomainVerificationId}"`.
2. At the DNS registrar add `CNAME api → <host>` and `TXT asuid.api → <verification>`.
3. Bind the name and add a free managed certificate:
   ```sh
   az webapp config hostname add -g $RG --webapp-name <app> --hostname api.supportivetherapy.network
   THUMB=$(az webapp config ssl create -g $RG --name <app> --hostname api.supportivetherapy.network --query thumbprint -o tsv)
   az webapp config ssl bind -g $RG --name <app> --certificate-thumbprint "$THUMB" --ssl-type SNI
   ```
4. Hostname bindings are not in the Bicep templates (they need DNS first); record them in the change log. If `allowedInboundCidrs` is set, confirm managed-certificate renewal still works.

## 9. Rollback

- **Application, same schema.** Run the workflow with phase **full** and `image_tag` set to the previous tag (each run summary records it; `az acr repository show-tags -n <registry> --repository stn-api --orderby time_desc`). The workflow reuses the image, runs it through the migrate slot (no migration applies) and moves the API back.
- **Application across a migration.** An older build reports not ready on a newer schema by design (it was not built for it). Either roll forward with a fix, or restore the database to a point before the migration (section 11 and the backup runbook) and then redeploy the older tag. Decide with the change owner; do not edit the schema by hand.
- **Infrastructure.** Revert the template change on `main` and run the workflow; Bicep deploys are incremental, so resources removed from the template are not deleted automatically. Delete them deliberately, after review.

## 10. Key rotation

Data keys (follow `backend/README.md` "Key rotation"):

1. Add `stn-data-key-2` to Key Vault (section 6 procedure).
2. In `staging.bicepparam` set `dataKeySecretNames = ['stn-data-key-1', 'stn-data-key-2']` and `activeDataKeyId = 'stn-data-key-2'`; merge and deploy. New writes use key 2.
3. As a staging admin, `POST /v1/admin/keys/re-encrypt` per organisation until `remaining` is 0; check `GET /v1/admin/keys/status`.
4. Remove key 1 from `dataKeySecretNames`; deploy. Disable (do not delete) the old secret and keep it, and its escrow copy, until no backup within retention needs it.

Redis access key: regenerate the key in the portal, run the workflow (it rewrites the Key Vault secret), then restart the app so the Key Vault reference is read again. Database: there is no password to rotate; access follows the managed identities. Deploy identity: nothing to rotate (federated credential); review its role assignments quarterly.

## 11. Staging restore drill

Run before go-live and after every schema migration (backup runbook section 5). Synthetic data only.

1. Note a target time, then restore to a **new** server in the same VNet:
   ```sh
   az postgres flexible-server restore -g $RG --name pg-stn-stg-drill-<date> \
     --source-server <pg-server> --restore-time "<UTC ISO 8601 time>"
   ```
2. Verify the restored copy from inside the network (`python -m app.verify_chain` returns `"ok": true`; `python -m app.rekey --verify-decrypt` returns `"failed": 0`; row counts as expected). The database accepts Entra tokens only: use `az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv` as the password for an operator who is an Entra administrator of the restored server.
3. Record the result, then delete the drill server.

The kit provisions **no operator access path into the VNet** (no Bastion, VPN or jump host), so step 2 needs one to be added first. Choosing it is an owner decision with a cost (section 14).

## 12. Troubleshooting and logs

- **Logs.** Log Analytics workspace `log-stn-stg-nzn`: `AppServiceConsoleLogs` (container output of the app and migrate slot), `AppServiceHTTPLogs`, `AppServicePlatformLogs`, PostgreSQL logs, Key Vault audit events, registry events. Logs contain no tokens or payloads by design; check before widening any log level.
- **Migrate slot never ready.** Look at its console log. `configuration error` means a setting is wrong; `migration failed: <ErrorClass>` gives the class only. A first run can fail with a permission error on schema `public` if the database's owner is not visible to the Entra administrator. That behaviour has not been verified against a live server; record what happens on the first deploy.
- **API not ready.** Its console log names the failed check (`database`, `keys`, `rate_limit`) and the exception class. `keys`: secret missing, wrong name, or role assignment still propagating. `rate_limit`: Redis private endpoint or DNS. `database`: schema not migrated, or the principal or grants missing (check the migrate slot ran).
- **Push denied.** The AcrPush assignment can take a few minutes to apply on the first run; re-run the workflow.
- **Preflight error.** Read the message: it names the missing or malformed variable. Nothing was changed.
- **Vault name conflict after recreating the resource group.** A deleted vault stays soft-deleted (purge protection) and keeps its name. Recover it with `az keyvault recover --name <vault>` before deploying again.

## 13. Costs to check (no prices are quoted here)

Use the Azure pricing calculator for New Zealand North and get the budget owner's approval before the first deploy. Items that cost money while they exist, even when idle:

- App Service plan (per instance, always on) and its tier.
- PostgreSQL Flexible Server compute, storage and backup storage beyond the included amount; zone-redundant HA roughly doubles compute.
- Azure Managed Redis (per hour, by SKU).
- Premium container registry (needed for private endpoints) and its storage.
- Three private endpoints (per hour and per GB processed) and four private DNS zones (per zone and per query volume).
- Log Analytics ingestion and retention beyond the included period.
- Key Vault operations.
- Outbound data transfer.
- Entra ID licences for Conditional Access (section 5), Microsoft Defender for Cloud plans if enabled, and GitHub Actions minutes if the repository becomes private.
- An operator access path into the VNet, if added (section 11).

Create a budget with alerts (infrastructure document section 6) and review usage monthly. Deleting the resource group stops these charges; purge protection keeps the vault's name reserved until its retention ends.

## 14. Open items (owner decisions)

- Accept or change the departures in section 1.
- Repository visibility before the first deploy (section 4).
- Operator access path into the VNet for restore drills and maintenance commands (section 11).
- `STN_TRUST_FORWARDED_FOR` stays off: App Service's front ends forward requests, so the per-IP limits currently see front-end addresses rather than clients. Enabling it safely needs confirmation of how App Service sets `X-Forwarded-For` (follow-up engineering change).
- Production: a production deploy workflow (deliberately absent), registry pushes from inside the network, zone-redundant HA and SKUs confirmed for New Zealand North, WAF/edge decision, image signing, and every go-live gate.
