// Production shape for review. There is deliberately no production deploy workflow yet: the
// go-live gate is not signed. SKUs are starting points to confirm with the Azure pricing
// calculator and capacity testing; zone-redundant HA must be checked for the chosen SKU in
// New Zealand North at deployment time.
using './main.bicep'

param environmentName = 'production'
param location = 'newzealandnorth'
param deployCompute = bool(readEnvironmentVariable('STN_DEPLOY_COMPUTE', 'false'))
param apiImageTag = readEnvironmentVariable('STN_API_IMAGE_TAG', '')
param migrateImageTag = readEnvironmentVariable('STN_MIGRATE_IMAGE_TAG', '')
param deployPrincipalObjectId = readEnvironmentVariable('STN_DEPLOY_PRINCIPAL_OBJECT_ID', '')

param logRetentionDays = 365
param postgresSkuName = 'Standard_D2ds_v5'
param postgresSkuTier = 'GeneralPurpose'
param postgresStorageGB = 128
param postgresBackupRetentionDays = 35
param postgresGeoRedundantBackup = 'Disabled'
param postgresHighAvailability = 'ZoneRedundant'

param redisEnabled = true
param redisSkuName = 'Balanced_B1'
// Push images from a runner inside the network before switching this to 'Disabled'.
param registryPublicNetworkAccess = 'Enabled'
param appServiceSkuName = 'P1v3'
param appInstanceCount = 2

param dataKeySecretNames = [ 'stn-data-key-1' ]
param activeDataKeyId = 'stn-data-key-1'

param oidcIssuer = readEnvironmentVariable('STN_OIDC_ISSUER', '')
param oidcAudience = readEnvironmentVariable('STN_OIDC_AUDIENCE', '')
param oidcJwksUrl = readEnvironmentVariable('STN_OIDC_JWKS_URL', '')
param idpEventAudience = readEnvironmentVariable('STN_IDP_EVENT_AUDIENCE', '')
param termsVersion = readEnvironmentVariable('STN_TERMS_VERSION', '')
param privacyNoticeVersion = readEnvironmentVariable('STN_PRIVACY_NOTICE_VERSION', '')
param consentVersion = readEnvironmentVariable('STN_CONSENT_VERSION', '')
param registerHosts = readEnvironmentVariable('STN_REGISTER_HOSTS', '')
param oidcRoleMap = readEnvironmentVariable('STN_OIDC_ROLE_MAP', '')
param oidcOrgClaim = readEnvironmentVariable('STN_OIDC_ORG_CLAIM', '')
param mfaAcrsValues = readEnvironmentVariable('STN_MFA_ACRS_VALUES', '')
param retentionPeriodDays = readEnvironmentVariable('STN_RETENTION_PERIOD_DAYS', '')
param privacyResponseWorkingDays = readEnvironmentVariable('STN_PRIVACY_RESPONSE_WORKING_DAYS', '')
param privacyExcludeSummerPeriod = readEnvironmentVariable('STN_PRIVACY_EXCLUDE_SUMMER_PERIOD', '')
param privacyNonWorkingDates = readEnvironmentVariable('STN_PRIVACY_NON_WORKING_DATES', '')
param bootstrapAdminOrg = readEnvironmentVariable('STN_BOOTSTRAP_ADMIN_ORG', '')
param bootstrapAdminSubject = readEnvironmentVariable('STN_BOOTSTRAP_ADMIN_SUBJECT', '')
