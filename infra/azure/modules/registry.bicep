// Container registry (Premium: private endpoint, retention). Admin user and anonymous pull are
// off; App Service pulls with its managed identity. A GitHub-hosted runner can push only while
// public network access is enabled (staging default); production should push from a runner
// inside the network and set publicNetworkAccess to 'Disabled'.
param location string
param tags object
param name string
param workspaceId string
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string
param pullPrincipalIds array
@description('Object id of the deployment identity that pushes images (empty: assign AcrPush yourself).')
param pushPrincipalId string

var acrPull = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var acrPush = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8311e382-0749-4cb8-b61a-304f252e45ec')

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Premium' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: publicNetworkAccess
    networkRuleBypassOptions: 'AzureServices'
    zoneRedundancy: 'Disabled'
    policies: {
      retentionPolicy: { days: 30, status: 'enabled' }
    }
  }
}

resource pulls 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in pullPrincipalIds: {
  scope: registry
  name: guid(registry.id, principalId, acrPull)
  properties: {
    roleDefinitionId: acrPull
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}]

resource push 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(pushPrincipalId)) {
  scope: registry
  name: guid(registry.id, pushPrincipalId, acrPush)
  properties: {
    roleDefinitionId: acrPush
    principalId: pushPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: registry
  name: 'to-log-analytics'
  properties: {
    workspaceId: workspaceId
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output id string = registry.id
output name string = registry.name
output loginServer string = registry.properties.loginServer
