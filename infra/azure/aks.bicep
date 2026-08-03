targetScope = 'resourceGroup'

@description('Azure Region')
param location string = resourceGroup().location

@description('AKS Cluster Name')
param aksName string = 'aiops-aks'

@description('DNS Prefix')
param dnsPrefix string = 'aiops'

@description('Subnet ID for AKS')
param subnetId string

@description('ACR Resource ID')
param acrId string

@description('Log Analytics Workspace Resource ID')
param logAnalyticsWorkspaceId string

@description('Node Count')
param nodeCount int = 2

@description('VM Size')
param vmSize string = 'Standard_B2as_v2'

resource aks 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: aksName
  location: location

  identity: {
    type: 'SystemAssigned'
  }

  properties: {

    dnsPrefix: dnsPrefix

    kubernetesVersion: ''

    agentPoolProfiles: [
      {
        name: 'system'

        mode: 'System'

        count: nodeCount

        vmSize: vmSize

        osType: 'Linux'

        type: 'VirtualMachineScaleSets'

        vnetSubnetID: subnetId
      }
    ]

   networkProfile: {
  networkPlugin: 'azure'
  serviceCidr: '10.240.0.0/16'
  dnsServiceIP: '10.240.0.10'
}

    addonProfiles: {
      omsAgent: {
        enabled: true

        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspaceId
        }
      }
    }
  }
}

resource acrRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, acrId, 'AcrPull')

  scope: resourceGroup()

  properties: {
    principalId: aks.identity.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalType: 'ServicePrincipal'
  }

  
}

output aksId string = aks.id
output aksName string = aks.name
