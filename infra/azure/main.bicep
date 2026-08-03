targetScope = 'resourceGroup'

param location string = resourceGroup().location

param acrName string
param storageAccountName string
param keyVaultName string

@secure()
param adminPassword string

param adminUsername string = 'azureuser'

module network './network.bicep' = {
  name: 'network'

  params: {
    location: location
  }
}

module acr './acr.bicep' = {
  name: 'acr'

  params: {
    location: location
    acrName: acrName
  }
}

module storage './storage.bicep' = {
  name: 'storage'

  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

module monitoring './monitoring.bicep' = {
  name: 'monitoring'

  params: {
    location: location
  }
}

module keyvault './keyvault.bicep' = {
  name: 'keyvault'

  params: {
    location: location
    keyVaultName: keyVaultName
  }
}

module vm './vm.bicep' = {
  name: 'vm'

  params: {
    location: location
    subnetId: network.outputs.vmSubnetId
    adminUsername: adminUsername
    adminPassword: adminPassword
  }
}

module aks './aks.bicep' = {
  name: 'aks'

  params: {
    location: location
    subnetId: network.outputs.aksSubnetId
    acrId: acr.outputs.acrId
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
  }

}

output aksName string = aks.outputs.aksName
output acrLoginServer string = acr.outputs.acrLoginServer
output storageName string = storage.outputs.storageAccountName
output keyVaultUri string = keyvault.outputs.vaultUri
output vmPublicIp string = vm.outputs.publicIPAddress
