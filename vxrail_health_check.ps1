# VxRail Health Check Script
# This script checks the health status of a VxRail cluster using the VxRail API
# Compatible with VxRail version 8.0.000 and later
# Author: Codeium
# Date: 2025-01-29

# Function to create basic authentication header
function Get-BasicAuthHeader {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [SecureString]$SecurePassword
    )
    
    try {
        # Convert SecureString password to plain text for basic auth
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
        $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        # Create base64 encoded credentials
        $Pair = "${Username}:${Password}"
        $Bytes = [System.Text.Encoding]::ASCII.GetBytes($Pair)
        $Base64 = [Convert]::ToBase64String($Bytes)
        
        return @{
            "Authorization" = "Basic $Base64"
            "Content-Type" = "application/json"
        }
    }
    catch {
        throw "Failed to create authentication header: $_"
    }
    finally {
        if ($BSTR) {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        }
    }
}

# Function to make API requests with error handling
function Invoke-VxRailAPI {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BaseURL,
        
        [Parameter(Mandatory=$true)]
        [string]$Endpoint,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Headers
    )
    
    try {
        # Disable SSL certificate validation (not recommended for production)
        if (-not ([System.Management.Automation.PSTypeName]'ServerCertificateValidationCallback').Type) {
            $CertCallback = @"
                using System;
                using System.Net;
                using System.Net.Security;
                using System.Security.Cryptography.X509Certificates;
                public class ServerCertificateValidationCallback
                {
                    public static void Ignore()
                    {
                        ServicePointManager.ServerCertificateValidationCallback += 
                            delegate
                            (
                                Object obj, 
                                X509Certificate certificate, 
                                X509Chain chain, 
                                SslPolicyErrors errors
                            )
                            {
                                return true;
                            };
                    }
                }
"@
            Add-Type $CertCallback
        }
        [ServerCertificateValidationCallback]::Ignore()
        
        # Make API request
        $URI = "${BaseURL}${Endpoint}"
        $Response = Invoke-RestMethod -Uri $URI -Headers $Headers -Method Get -SkipCertificateCheck
        return $Response
    }
    catch {
        $StatusCode = $_.Exception.Response.StatusCode.value__
        $StatusDescription = $_.Exception.Response.StatusDescription
        
        switch ($StatusCode) {
            401 { throw "Authentication failed. Please check your credentials." }
            403 { throw "Access forbidden. Please check your permissions." }
            404 { throw "Endpoint not found: $URI" }
            default { throw "API request failed: $StatusCode - $StatusDescription. Error: $_" }
        }
    }
}

# Function to check VxRail version
function Get-VxRailVersion {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BaseURL,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Headers
    )
    
    try {
        Write-Host "`nChecking VxRail version..." -ForegroundColor Cyan
        $Response = Invoke-VxRailAPI -BaseURL $BaseURL -Endpoint "/rest/vxm/v1/system" -Headers $Headers
        
        if ($Response.version) {
            Write-Host "VxRail Version: $($Response.version)" -ForegroundColor Green
            return $Response.version
        }
        else {
            throw "Unable to determine VxRail version"
        }
    }
    catch {
        Write-Warning "Failed to check VxRail version: $_"
        return $null
    }
}

# Function to check cluster health
function Get-ClusterHealth {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BaseURL,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Headers
    )
    
    try {
        Write-Host "`nChecking cluster health..." -ForegroundColor Cyan
        $Response = Invoke-VxRailAPI -BaseURL $BaseURL -Endpoint "/rest/vxm/v1/cluster" -Headers $Headers
        
        $Health = $Response.health
        Write-Host "Cluster Health Status: $Health" -ForegroundColor $(if ($Health -eq "healthy") { "Green" } else { "Red" })
        return $Health -eq "healthy"
    }
    catch {
        Write-Warning "Failed to check cluster health: $_"
        return $false
    }
}

# Function to check hosts health
function Get-HostsHealth {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BaseURL,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Headers
    )
    
    try {
        Write-Host "`nChecking hosts health..." -ForegroundColor Cyan
        $Response = Invoke-VxRailAPI -BaseURL $BaseURL -Endpoint "/rest/vxm/v16/hosts" -Headers $Headers
        
        $AllHealthy = $true
        foreach ($Host in $Response) {
            $HostName = $Host.hostname
            $Health = $Host.health
            $PowerStatus = $Host.power_status
            $TpmVersion = $Host.tpm_version
            $TpmStatus = $Host.tpm_status
            
            Write-Host "`nHost: $HostName" -ForegroundColor Yellow
            Write-Host "Health Status: $Health" -ForegroundColor $(if ($Health -eq "healthy") { "Green" } else { "Red" })
            Write-Host "Power Status: $PowerStatus"
            Write-Host "TPM Version: $TpmVersion"
            Write-Host "TPM Status: $TpmStatus"
            
            if ($Health -ne "healthy") {
                $AllHealthy = $false
            }
        }
        
        return $AllHealthy
    }
    catch {
        Write-Warning "Failed to check hosts health: $_"
        return $false
    }
}

# Function to check storage health using host disk information
function Get-StorageHealth {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BaseURL,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Headers
    )
    
    try {
        Write-Host "`nChecking storage health..." -ForegroundColor Cyan
        $Response = Invoke-VxRailAPI -BaseURL $BaseURL -Endpoint "/rest/vxm/v16/hosts" -Headers $Headers
        
        $AllHealthy = $true
        $StorageInfo = @{}  # Track unique disks by serial number
        
        foreach ($Host in $Response) {
            $HostName = $Host.hostname
            Write-Host "`nHost: $HostName" -ForegroundColor Yellow
            
            foreach ($Disk in $Host.disks) {
                $SerialNumber = $Disk.sn
                if (-not $StorageInfo.ContainsKey($SerialNumber)) {
                    $DiskState = $Disk.disk_state
                    $DiskType = $Disk.disk_type
                    $DiskTier = $Disk.disk_tier
                    $Capacity = $Disk.capacity
                    
                    Write-Host "`nDisk SN: $SerialNumber"
                    Write-Host "State: $DiskState" -ForegroundColor $(if ($DiskState -eq "OK") { "Green" } else { "Red" })
                    Write-Host "Type: $DiskType"
                    Write-Host "Tier: $DiskTier"
                    Write-Host "Capacity: $Capacity"
                    
                    if ($DiskState -ne "OK") {
                        $AllHealthy = $false
                        Write-Warning "Disk $SerialNumber is in $DiskState state"
                    }
                    
                    $StorageInfo[$SerialNumber] = $DiskState
                }
            }
        }
        
        return $AllHealthy
    }
    catch {
        Write-Warning "Failed to check storage health: $_"
        return $false
    }
}

# Main script execution
try {
    # Get VxRail Manager details
    $VxRailHost = Read-Host "Enter VxRail Manager IP or hostname"
    $Username = Read-Host "Enter username"
    $SecurePassword = Read-Host "Enter password" -AsSecureString
    
    # Construct base URL
    $BaseURL = "https://$VxRailHost"
    
    # Create authentication headers
    $Headers = Get-BasicAuthHeader -Username $Username -SecurePassword $SecurePassword
    
    Write-Host "`nStarting VxRail Health Check..." -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "-" * 50
    
    # Check VxRail version first
    $Version = Get-VxRailVersion -BaseURL $BaseURL -Headers $Headers
    if ($Version) {
        if ([version]$Version -lt [version]"8.0.000") {
            Write-Warning "This script is optimized for VxRail 8.0.000 or later. Current version: $Version"
            Write-Warning "Some features may not be available."
        }
    }
    else {
        Write-Warning "Failed to determine VxRail version. Health check may not be accurate."
    }
    
    # Perform health checks
    $ClusterHealthy = Get-ClusterHealth -BaseURL $BaseURL -Headers $Headers
    $HostsHealthy = Get-HostsHealth -BaseURL $BaseURL -Headers $Headers
    $StorageHealthy = Get-StorageHealth -BaseURL $BaseURL -Headers $Headers
    
    # Print summary
    Write-Host "`nHealth Check Summary:" -ForegroundColor Cyan
    Write-Host "-" * 50
    Write-Host "Cluster Health: $(if ($ClusterHealthy) { "✓ Healthy" } else { "✗ Unhealthy" })" -ForegroundColor $(if ($ClusterHealthy) { "Green" } else { "Red" })
    Write-Host "Hosts Health: $(if ($HostsHealthy) { "✓ Healthy" } else { "✗ Unhealthy" })" -ForegroundColor $(if ($HostsHealthy) { "Green" } else { "Red" })
    Write-Host "Storage Health: $(if ($StorageHealthy) { "✓ Healthy" } else { "✗ Unhealthy" })" -ForegroundColor $(if ($StorageHealthy) { "Green" } else { "Red" })
    
    # Overall system status
    $SystemHealthy = $ClusterHealthy -and $HostsHealthy -and $StorageHealthy
    Write-Host "`nOverall System Status: $(if ($SystemHealthy) { "✓ HEALTHY" } else { "✗ ATTENTION REQUIRED" })" -ForegroundColor $(if ($SystemHealthy) { "Green" } else { "Red" })
}
catch {
    Write-Error "An error occurred during the health check: $_"
    exit 1
}
