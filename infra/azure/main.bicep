// STN API platform on Azure (resource-group scope). Synthetic data only until every production
// go-live gate is signed (docs/release/PRODUCTION-GO-LIVE-GATE.md).
//
// Two phases, both from this template (see .github/workflows/deploy-staging.yml):
//   deployCompute = false  foundation: network, private DNS, monitoring, identities, Key Vault,
//                          registry, PostgreSQL and (optionally) Azure Managed Redis
//   deployCompute = true   also App Service: the API, and the 'migrate' slot that applies
//                          migrations before the API image changes
//
// No secrets are parameters. The database uses Microsoft Entra authentication only; the Redis
// connection string is written into Key Vault by the deployment; data-encryption keys are added
// to Key Vault by an operator (docs/operations/DEPLOYMENT-RUNBOOK.md).
targetScope = 'resourceGroup'

@allowed([ 'staging', 'production' ])
param environmentName string

@description('Azure region. New Zealand North keeps the database and keys in New Zealand.')
#disable-next-line no-hardcoded-location
param location string = 'newzealandnorth'

param tags object = {}

@description('false: foundation only. true: also the App Service API and migrate slot.')
param deployCompute bool = false
@maxLength(128)
@description('Image tag the API slot runs (stn-api:<tag> in the registry).')
param apiImageTag string = ''
@maxLength(128)
@description('Image tag the migrate slot runs.')
param migrateImageTag string = ''

// Network
param vnetAddressPrefix string = '10.60.0.0/16'
param appSubnetPrefix string = '10.60.1.0/24'
param postgresSubnetPrefix string = '10.60.2.0/24'
param privateEndpointSubnetPrefix string = '10.60.3.0/24'

// Monitoring
@minValue(30)
@maxValue(730)
param logRetentionDays int = 90

// PostgreSQL
param postgresSkuName string = 'Standard_B1ms'
@allowed([ 'Burstable', 'GeneralPurpose', 'MemoryOptimized' ])
param postgresSkuTier string = 'Burstable'
param postgresStorageGB int = 32
@minValue(7)
@maxValue(35)
param postgresBackupRetentionDays int = 7
@description('Keep Disabled: New Zealand North is non-paired, so geo-redundant backups would leave New Zealand. Enable only with privacy-officer and legal approval.')
@allowed([ 'Disabled', 'Enabled' ])
param postgresGeoRedundantBackup string = 'Disabled'
@allowed([ 'Disabled', 'ZoneRedundant', 'SameZone' ])
param postgresHighAvailability string = 'Disabled'

// Redis (shared rate-limit store). Without it, run exactly one API instance.
param redisEnabled bool = true
param redisSkuName string = 'Balanced_B0'

// Registry
@allowed([ 'Enabled', 'Disabled' ])
param registryPublicNetworkAccess string = 'Enabled'
@description('Object id of the GitHub deployment identity (gets AcrPush). Empty: assign it yourself.')
param deployPrincipalObjectId string = ''

// Key Vault
@description('Temporary operator IPv4 addresses allowed through the Key Vault firewall while adding keys. Leave empty normally.')
param keyVaultAllowedIps array = []
@description('Key Vault secret names holding the data-encryption keys (each name is the key id).')
param dataKeySecretNames array = [ 'stn-data-key-1' ]
param activeDataKeyId string = 'stn-data-key-1'

// App Service
param appServiceSkuName string = 'P0v3'
@minValue(1)
param appInstanceCount int = 1
param appZoneRedundant bool = false
@description('Optional inbound CIDR allow-list for the API. Empty: public HTTPS ingress.')
param allowedInboundCidrs array = []

// API configuration (non-secret). Empty values are left out of the app settings.
param oidcIssuer string = ''
param oidcAudience string = ''
param oidcJwksUrl string = ''
param oidcRoleMap string = ''
param oidcOrgClaim string = ''
param mfaAcrsValues string = ''
@description('Only the value confirmed by legal advice. Empty: disposal stays disabled.')
param retentionPeriodDays string = ''
@description('Only the value confirmed by the privacy officer. Empty: requests get no due date.')
param privacyResponseWorkingDays string = ''
param privacyExcludeSummerPeriod string = ''
param privacyNonWorkingDates string = ''

@description('First account to register and activate in the clinician registry (migrate slot only; never changes an existing account). Empty: none.')
param bootstrapAdminOrg string = ''
param bootstrapAdminSubject string = ''

var envShort = environmentName == 'production' ? 'prod' : 'stg'
var suffix = take(uniqueString(resourceGroup().id), 8)
var allTags = union({
  organisation: 'STN'
  environment: environmentName
  'data-classification': 'health-information'
  owner: 'STN'
  'managed-by': 'bicep'
}, tags)

var names = {
  workspace: 'log-stn-${envShort}-nzn'
  vnet: 'vnet-stn-${envShort}-nzn'
  apiIdentity: 'id-stn-api-${envShort}'
  migrateIdentity: 'id-stn-migrate-${envShort}'
  keyVault: 'kv-stn-${envShort}-${suffix}'
  registry: 'acrstn${envShort}${suffix}'
  postgres: 'pg-stn-${envShort}-${suffix}'
  redis: 'redis-stn-${envShort}-${suffix}'
  plan: 'asp-stn-${envShort}-nzn'
  app: 'app-stn-api-${envShort}-${suffix}'
}
var databaseName = 'stn'
var redisSecretName = 'stn-redis-url'
var deployComputeNow = deployCompute && !empty(apiImageTag) && !empty(migrateImageTag)

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: { location: location, tags: allTags, name: names.workspace, retentionDays: logRetentionDays }
}

module network 'modules/network.bicep' = {
  name: 'network'
  params: {
    location: location
    tags: allTags
    vnetName: names.vnet
    addressPrefix: vnetAddressPrefix
    appSubnetPrefix: appSubnetPrefix
    postgresSubnetPrefix: postgresSubnetPrefix
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
  }
}

module identities 'modules/identities.bicep' = {
  name: 'identities'
  params: {
    location: location
    tags: allTags
    apiIdentityName: names.apiIdentity
    migrateIdentityName: names.migrateIdentity
  }
}

module keyVaultZone 'modules/privateDnsZone.bicep' = {
  name: 'dns-keyvault'
  params: { zoneName: 'privatelink${replace(environment().suffixes.keyvaultDns, 'vault.', 'vaultcore.')}', vnetId: network.outputs.vnetId, tags: allTags }
}

module registryZone 'modules/privateDnsZone.bicep' = {
  name: 'dns-registry'
  params: { zoneName: 'privatelink${environment().suffixes.acrLoginServer}', vnetId: network.outputs.vnetId, tags: allTags }
}

module postgresZone 'modules/privateDnsZone.bicep' = {
  name: 'dns-postgres'
  params: { zoneName: '${names.postgres}.private.postgres.database.azure.com', vnetId: network.outputs.vnetId, tags: allTags }
}

module redisZone 'modules/privateDnsZone.bicep' = if (redisEnabled) {
  name: 'dns-redis'
  params: { zoneName: 'privatelink.redis.azure.net', vnetId: network.outputs.vnetId, tags: allTags }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    tags: allTags
    name: names.keyVault
    tenantId: tenant().tenantId
    workspaceId: monitoring.outputs.workspaceId
    apiPrincipalId: identities.outputs.apiPrincipalId
    allowedIps: keyVaultAllowedIps
  }
}

module keyVaultEndpoint 'modules/privateEndpoint.bicep' = {
  name: 'pe-keyvault'
  params: {
    location: location
    tags: allTags
    name: 'pe-${names.keyVault}'
    subnetId: network.outputs.endpointSubnetId
    targetResourceId: keyVault.outputs.id
    groupId: 'vault'
    privateDnsZoneId: keyVaultZone.outputs.zoneId
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    location: location
    tags: allTags
    name: names.registry
    workspaceId: monitoring.outputs.workspaceId
    publicNetworkAccess: registryPublicNetworkAccess
    pullPrincipalIds: [ identities.outputs.apiPrincipalId, identities.outputs.migratePrincipalId ]
    pushPrincipalId: deployPrincipalObjectId
  }
}

module registryEndpoint 'modules/privateEndpoint.bicep' = {
  name: 'pe-registry'
  params: {
    location: location
    tags: allTags
    name: 'pe-${names.registry}'
    subnetId: network.outputs.endpointSubnetId
    targetResourceId: registry.outputs.id
    groupId: 'registry'
    privateDnsZoneId: registryZone.outputs.zoneId
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    tags: allTags
    name: names.postgres
    tenantId: tenant().tenantId
    workspaceId: monitoring.outputs.workspaceId
    delegatedSubnetId: network.outputs.postgresSubnetId
    privateDnsZoneId: postgresZone.outputs.zoneId
    skuName: postgresSkuName
    skuTier: postgresSkuTier
    storageSizeGB: postgresStorageGB
    backupRetentionDays: postgresBackupRetentionDays
    geoRedundantBackup: postgresGeoRedundantBackup
    highAvailability: postgresHighAvailability
    adminPrincipalId: identities.outputs.migratePrincipalId
    adminPrincipalName: identities.outputs.migrateName
    databaseName: databaseName
  }
}

module redis 'modules/redis.bicep' = if (redisEnabled) {
  name: 'redis'
  params: {
    location: location
    tags: allTags
    name: names.redis
    skuName: redisSkuName
    keyVaultName: keyVault.outputs.name
    secretName: redisSecretName
  }
}

module redisEndpoint 'modules/privateEndpoint.bicep' = if (redisEnabled) {
  name: 'pe-redis'
  params: {
    location: location
    tags: allTags
    name: 'pe-${names.redis}'
    subnetId: network.outputs.endpointSubnetId
    targetResourceId: redis!.outputs.id
    groupId: 'redisEnterprise'
    privateDnsZoneId: redisZone!.outputs.zoneId
  }
}

var optionalApiSettings = {
  STN_OIDC_ISSUER: oidcIssuer
  STN_OIDC_AUDIENCE: oidcAudience
  STN_OIDC_JWKS_URL: oidcJwksUrl
  STN_OIDC_ROLE_MAP: oidcRoleMap
  STN_OIDC_ORG_CLAIM: oidcOrgClaim
  STN_MFA_ACRS_VALUES: mfaAcrsValues
  STN_RETENTION_PERIOD_DAYS: retentionPeriodDays
  STN_PRIVACY_RESPONSE_WORKING_DAYS: privacyResponseWorkingDays
  STN_PRIVACY_EXCLUDE_SUMMER_PERIOD: privacyExcludeSummerPeriod
  STN_PRIVACY_NON_WORKING_DATES: privacyNonWorkingDates
}

var apiSettings = union(
  {
    WEBSITES_PORT: '8000'
    WEBSITES_ENABLE_APP_SERVICE_STORAGE: 'false'
    STN_PROCESS_ROLE: 'api'
    STN_ENVIRONMENT: environmentName
    AZURE_CLIENT_ID: identities.outputs.apiClientId
    STN_DATABASE_URL: 'postgresql://${names.apiIdentity}@${postgres.outputs.fqdn}:5432/${databaseName}?sslmode=require'
    STN_DATABASE_AUTH: 'azure-managed-identity'
    STN_DATABASE_AUTO_MIGRATE: 'false'
    STN_KEY_PROVIDER: 'azure-keyvault'
    STN_KEYVAULT_URL: keyVault.outputs.uri
    STN_KEYVAULT_KEY_IDS: join(dataKeySecretNames, ',')
    STN_DATA_ACTIVE_KEY_ID: activeDataKeyId
    STN_RATE_LIMIT_BACKEND: redisEnabled ? 'redis' : 'memory'
    STN_REQUIRE_MFA: 'true'
    STN_ACCOUNT_REGISTRY_REQUIRED: 'true'
    STN_REVIEW_ASSIGNMENT_REQUIRED: 'true'
  },
  redisEnabled ? { STN_REDIS_URL: '@Microsoft.KeyVault(SecretUri=${redis!.outputs.secretUri})' } : {},
  toObject(filter(items(optionalApiSettings), s => !empty(s.value)), s => s.key, s => s.value)
)

var migrateSettings = union(
  {
    WEBSITES_PORT: '8000'
    WEBSITES_ENABLE_APP_SERVICE_STORAGE: 'false'
    STN_PROCESS_ROLE: 'migrate'
    STN_ENVIRONMENT: environmentName
    AZURE_CLIENT_ID: identities.outputs.migrateClientId
    STN_DATABASE_URL: 'postgresql://${names.migrateIdentity}@${postgres.outputs.fqdn}:5432/${databaseName}?sslmode=require'
    STN_DATABASE_AUTH: 'azure-managed-identity'
    STN_DB_RUNTIME_ROLE: names.apiIdentity
    STN_DB_CREATE_ENTRA_PRINCIPAL: 'true'
  },
  empty(bootstrapAdminOrg) || empty(bootstrapAdminSubject) ? {} : {
    STN_BOOTSTRAP_ADMIN_ORG: bootstrapAdminOrg
    STN_BOOTSTRAP_ADMIN_SUBJECT: bootstrapAdminSubject
  }
)

module compute 'modules/appservice.bicep' = if (deployComputeNow) {
  name: 'compute'
  dependsOn: [ keyVaultEndpoint, registryEndpoint, redisEndpoint ]
  params: {
    location: location
    tags: allTags
    planName: names.plan
    appName: names.app
    skuName: appServiceSkuName
    instanceCount: redisEnabled ? appInstanceCount : 1
    zoneRedundant: appZoneRedundant
    appSubnetId: network.outputs.appSubnetId
    workspaceId: monitoring.outputs.workspaceId
    registryLoginServer: registry.outputs.loginServer
    apiImageTag: apiImageTag
    migrateImageTag: migrateImageTag
    apiIdentityId: identities.outputs.apiId
    apiIdentityClientId: identities.outputs.apiClientId
    migrateIdentityId: identities.outputs.migrateId
    migrateIdentityClientId: identities.outputs.migrateClientId
    apiSettings: apiSettings
    migrateSettings: migrateSettings
    allowedInboundCidrs: allowedInboundCidrs
  }
}

output appName string = names.app
output migrateSlotName string = 'migrate'
output registryName string = registry.outputs.name
output registryLoginServer string = registry.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output postgresServerName string = postgres.outputs.name
output apiIdentityName string = names.apiIdentity
output migrateIdentityName string = names.migrateIdentity
