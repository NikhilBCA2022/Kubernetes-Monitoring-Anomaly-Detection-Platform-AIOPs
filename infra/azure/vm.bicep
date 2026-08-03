targetScope = 'resourceGroup'

@description('Azure Region')
param location string = resourceGroup().location

@description('VM Name')
param vmName string = 'aiops-vm'

@description('Admin Username')
param adminUsername string

@secure()
@description('Admin Password')
param adminPassword string

@description('Subnet ID')
param subnetId string

@description('VM Size')
param vmSize string = 'Standard_B2as_v2'

resource publicIP 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: '${vmName}-pip'
  location: location

  sku: {
    name: 'Standard'
  }

  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: '${vmName}-nic'
  location: location

  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'

        properties: {
          subnet: {
            id: subnetId
          }

          privateIPAllocationMethod: 'Dynamic'

          publicIPAddress: {
            id: publicIP.id
          }
        }
      }
    ]
  }
}

resource virtualMachine 'Microsoft.Compute/virtualMachines@2023-07-01' = {
  name: vmName
  location: location

  properties: {

    hardwareProfile: {
      vmSize: vmSize
    }

    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      adminPassword: adminPassword

      linuxConfiguration: {
        disablePasswordAuthentication: false
      }
    }

    storageProfile: {

      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }

      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
      }
    }

    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
        }
      ]
    }
  }
}

output vmId string = virtualMachine.id
output vmName string = virtualMachine.name
output publicIPAddress string = publicIP.properties.ipAddress
