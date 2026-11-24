// Two user-assigned managed identities, so the API never holds schema-change rights:
// - api:     runs the API; database data privileges only; reads data keys from Key Vault.
// - migrate: runs migrations in the 'migrate' slot; Microsoft Entra administrator of the
//            PostgreSQL server; no Key Vault access.
param location string
param tags object
param apiIdentityName string
param migrateIdentityName string

resource api 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: apiIdentityName
  location: location
  tags: tags
}

resource migrate 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: migrateIdentityName
  location: location
  tags: tags
}

output apiId string = api.id
output apiName string = api.name
output apiClientId string = api.properties.clientId
output apiPrincipalId string = api.properties.principalId
output migrateId string = migrate.id
output migrateName string = migrate.name
output migrateClientId string = migrate.properties.clientId
output migratePrincipalId string = migrate.properties.principalId
