// Evidence storage (D-13, D-18): write-once containers for audit-chain exports and logical database dumps.
//
// - Time-based retention (WORM) on each container. Policies are created UNLOCKED: locking is irreversible
//   (it cannot be shortened or removed, and the account cannot be deleted while blobs are retained), so the
//   owner locks them deliberately after a successful test (docs/operations/IMMUTABLE-AUDIT-RETENTION.md).
// - audit-exports allows protected append writes so a day's export can be appended, never rewritten.
// - No shared keys, no public network access, no anonymous blob access, TLS 1.2+, HTTPS only.
//   Access is by managed identity (Entra RBAC) through a private endpoint.
// - Blob versioning plus soft delete as a second line behind WORM; diagnostics to Log Analytics.
// Nothing is deployed unless main.bicep sets deployEvidenceStorage = true.
param location string
param tags object
param name string
param skuName string
param workspaceId string
@description('Principal that writes exports and dumps (the operations/migrate identity).')
param writerPrincipalId string
@minValue(1)
param auditRetentionDays int
@minValue(1)
param dumpRetentionDays int

resource account 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: skuName }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Cool'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Disabled'
    allowCrossTenantReplication: false
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
    encryption: {
      keySource: 'Microsoft.Storage'
      requireInfrastructureEncryption: true
      services: { blob: { enabled: true, keyType: 'Account' } }
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: account
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: { enabled: true, days: 30 }
    containerDeleteRetentionPolicy: { enabled: true, days: 30 }
  }
}

resource auditContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'audit-exports'
  properties: { publicAccess: 'None' }
}

resource auditPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: auditContainer
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: auditRetentionDays
    allowProtectedAppendWrites: true
  }
}

resource dumpContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'db-dumps'
  properties: { publicAccess: 'None' }
}

resource dumpPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: dumpContainer
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: dumpRetentionDays
    allowProtectedAppendWrites: false
  }
}

// Storage Blob Data Contributor: can create and read blobs; WORM prevents overwrite and deletion.
var blobContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource writerAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, writerPrincipalId, blobContributorRole)
  properties: {
    principalId: writerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributorRole)
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: blobService
  name: 'to-log-analytics'
  properties: {
    workspaceId: workspaceId
    logs: [
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
      { category: 'StorageRead', enabled: true }
    ]
    metrics: [ { category: 'Transaction', enabled: true } ]
  }
}

output id string = account.id
output name string = account.name
output blobEndpoint string = account.properties.primaryEndpoints.blob
