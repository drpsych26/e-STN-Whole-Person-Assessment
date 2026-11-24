// Key Vault for the API's data-encryption keys and the Redis connection string.
// RBAC authorisation, soft delete and purge protection; reachable only through its private
// endpoint, except from the IP addresses an operator lists while adding keys (see the runbook).
param location string
param tags object
param name string
param tenantId string
param workspaceId string
param apiPrincipalId string
@description('Temporary operator IPv4 addresses allowed through the vault firewall (empty: no public access).')
param allowedIps array

var keyVaultSecretsUser = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: empty(allowedIps) ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
      ipRules: [for ip in allowedIps: { value: ip }]
    }
  }
}

resource apiReadsSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vault
  name: guid(vault.id, apiPrincipalId, keyVaultSecretsUser)
  properties: {
    roleDefinitionId: keyVaultSecretsUser
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: vault
  name: 'to-log-analytics'
  properties: {
    workspaceId: workspaceId
    logs: [ { categoryGroup: 'audit', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output id string = vault.id
output name string = vault.name
output uri string = vault.properties.vaultUri
