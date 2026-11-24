// Virtual network for STN: App Service integration, PostgreSQL (delegated), private endpoints.
// No subnet is reachable from the internet; the API's public ingress is App Service's front end.
param location string
param tags object
param vnetName string
param addressPrefix string
param appSubnetPrefix string
param postgresSubnetPrefix string
param privateEndpointSubnetPrefix string

resource nsgApp 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${vnetName}-app'
  location: location
  tags: tags
}

resource nsgPostgres 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${vnetName}-pg'
  location: location
  tags: tags
}

resource nsgEndpoints 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${vnetName}-pe'
  location: location
  tags: tags
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: [ addressPrefix ] }
    subnets: [
      {
        name: 'snet-app'
        properties: {
          addressPrefix: appSubnetPrefix
          networkSecurityGroup: { id: nsgApp.id }
          delegations: [ { name: 'web', properties: { serviceName: 'Microsoft.Web/serverFarms' } } ]
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          networkSecurityGroup: { id: nsgPostgres.id }
          delegations: [ { name: 'postgres', properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } } ]
        }
      }
      {
        name: 'snet-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          networkSecurityGroup: { id: nsgEndpoints.id }
          privateEndpointNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output appSubnetId string = vnet.properties.subnets[0].id
output postgresSubnetId string = vnet.properties.subnets[1].id
output endpointSubnetId string = vnet.properties.subnets[2].id
