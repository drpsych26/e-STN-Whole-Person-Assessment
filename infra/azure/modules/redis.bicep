// Azure Managed Redis for the shared rate-limit store (Azure Cache for Redis Basic/Standard/
// Premium retire on 30 September 2028; Microsoft recommends Azure Managed Redis for new work).
// TLS only, no public access; the connection string is written straight into Key Vault by this
// deployment, so no person or pipeline log ever handles the access key.
param location string
param tags object
param name string
param skuName string
param keyVaultName string
param secretName string

resource cluster 'Microsoft.Cache/redisEnterprise@2025-07-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: skuName }
  properties: {
    minimumTlsVersion: '1.2'
    highAvailability: 'Enabled'
    publicNetworkAccess: 'Disabled'
  }
}

resource database 'Microsoft.Cache/redisEnterprise/databases@2025-07-01' = {
  parent: cluster
  name: 'default'
  properties: {
    clientProtocol: 'Encrypted'
    port: 10000
    clusteringPolicy: 'EnterpriseCluster'
    evictionPolicy: 'VolatileLRU'
    accessKeysAuthentication: 'Enabled'
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource connectionString 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: secretName
  properties: {
    contentType: 'redis-url'
    value: 'rediss://:${database.listKeys().primaryKey}@${cluster.properties.hostName}:10000/0'
  }
}

output id string = cluster.id
output secretUri string = connectionString.properties.secretUri
