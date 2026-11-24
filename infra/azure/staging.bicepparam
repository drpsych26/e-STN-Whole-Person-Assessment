// Staging: smallest production-shaped footprint. Image tags, the compute switch and the API's
// non-secret configuration come from the deploy workflow's environment (GitHub variables).
using './main.bicep'

param environmentName = 'staging'
param location = 'newzealandnorth'
param deployCompute = bool(readEnvironmentVariable('STN_DEPLOY_COMPUTE', 'false'))
param apiImageTag = readEnvironmentVariable('STN_API_IMAGE_TAG', '')
param migrateImageTag = readEnvironmentVariable('STN_MIGRATE_IMAGE_TAG', '')
param deployPrincipalObjectId = readEnvironmentVariable('STN_DEPLOY_PRINCIPAL_OBJECT_ID', '')

param postgresSkuName = 'Standard_B1ms'
param postgresSkuTier = 'Burstable'
param postgresStorageGB = 32
param postgresBackupRetentionDays = 7
param postgresGeoRedundantBackup = 'Disabled'
param postgresHighAvailability = 'Disabled'

param redisEnabled = true
param redisSkuName = 'Balanced_B0'
param registryPublicNetworkAccess = 'Enabled'
param appServiceSkuName = 'P0v3'
param appInstanceCount = 1

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
