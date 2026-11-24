// Log Analytics workspace for platform and security logs. Clinical payloads are never logged
// by the API; retention here is for operational and audit telemetry only.
param location string
param tags object
param name string
@minValue(30)
@maxValue(730)
param retentionDays int

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: retentionDays
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
  }
}

output workspaceId string = workspace.id
