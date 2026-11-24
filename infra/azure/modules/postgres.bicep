// Azure Database for PostgreSQL Flexible Server: private access only (delegated subnet), TLS
// required, Microsoft Entra authentication only (no passwords). The migration identity is the
// Entra administrator; the migration step creates the API's runtime role with data privileges
// only (backend/app/migrate.py).
param location string
param tags object
param name string
param tenantId string
param workspaceId string
param delegatedSubnetId string
param privateDnsZoneId string
param skuName string
@allowed([ 'Burstable', 'GeneralPurpose', 'MemoryOptimized' ])
param skuTier string
param storageSizeGB int
@minValue(7)
@maxValue(35)
param backupRetentionDays int
@description('New Zealand North is a non-paired region. Keep Disabled unless the privacy officer and legal adviser have approved storing backups outside New Zealand.')
@allowed([ 'Disabled', 'Enabled' ])
param geoRedundantBackup string
@allowed([ 'Disabled', 'ZoneRedundant', 'SameZone' ])
param highAvailability string
param adminPrincipalId string
param adminPrincipalName string
param databaseName string

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: skuName, tier: skuTier }
  properties: {
    version: '16'
    storage: { storageSizeGB: storageSizeGB, autoGrow: 'Enabled' }
    backup: { backupRetentionDays: backupRetentionDays, geoRedundantBackup: geoRedundantBackup }
    highAvailability: { mode: highAvailability }
    network: {
      delegatedSubnetResourceId: delegatedSubnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
      publicNetworkAccess: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenantId
    }
  }
}

resource tls 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'require_secure_connection'
  properties: { value: 'on', source: 'user-override' }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
  parent: server
  name: adminPrincipalId
  dependsOn: [ tls ]
  properties: {
    principalType: 'ServicePrincipal'
    principalName: adminPrincipalName
    tenantId: tenantId
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: server
  name: 'to-log-analytics'
  properties: {
    workspaceId: workspaceId
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output fqdn string = server.properties.fullyQualifiedDomainName
output name string = server.name
output databaseName string = database.name
