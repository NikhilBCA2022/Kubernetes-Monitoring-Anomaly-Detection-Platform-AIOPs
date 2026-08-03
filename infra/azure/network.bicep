targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Virtual Network Name')
param vnetName string = 'aiops-vnet'

@description('Address Space')
param addressPrefix string = '10.0.0.0/16'

@description('AKS Subnet')
param aksSubnetPrefix string = '10.0.1.0/24'

@description('VM Subnet')
param vmSubnetPrefix string = '10.0.2.0/24'

@description('Azure Bastion Subnet')
param bastionSubnetPrefix string = '10.0.3.0/27'

@description('NSG Name')
param nsgName string = 'aiops-nsg'

resource networkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: nsgName
  location: location

  properties: {
    securityRules: [

      {
        name: 'Allow-SSH'
        properties: {
          priority: 100
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }

      {
        name: 'Allow-HTTP'
        properties: {
          priority: 110
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '80'
        }
      }

      {
        name: 'Allow-HTTPS'
        properties: {
          priority: 120
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }

      {
        name: 'Allow-Kubernetes'
        properties: {
          priority: 130
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '6443'
        }
      }

    ]
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location

  properties: {

    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }

    subnets: [

      {
        name: 'aks-subnet'

        properties: {
          addressPrefix: aksSubnetPrefix

          networkSecurityGroup: {
            id: networkSecurityGroup.id
          }
        }
      }

      {
        name: 'vm-subnet'

        properties: {
          addressPrefix: vmSubnetPrefix

          networkSecurityGroup: {
            id: networkSecurityGroup.id
          }
        }
      }

      {
        name: 'AzureBastionSubnet'

        properties: {
          addressPrefix: bastionSubnetPrefix
        }
      }

    ]
  }
}

output vnetId string = virtualNetwork.id

output aksSubnetId string = virtualNetwork.properties.subnets[0].id

output vmSubnetId string = virtualNetwork.properties.subnets[1].id

output bastionSubnetId string = virtualNetwork.properties.subnets[2].id

output nsgId string = networkSecurityGroup.id
