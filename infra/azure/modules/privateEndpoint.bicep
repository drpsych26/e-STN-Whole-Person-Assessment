// Private endpoint for a PaaS resource, registered in its private DNS zone.
param location string
param tags object
param name string
param subnetId string
param targetResourceId string
param groupId string
param privateDnsZoneId string

resource endpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: name
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: [ groupId ]
        }
      }
    ]
  }
}

resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: endpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [ { name: 'zone', properties: { privateDnsZoneId: privateDnsZoneId } } ]
  }
}
