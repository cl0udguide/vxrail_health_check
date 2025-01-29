# Get-VxRailSystemInfo.ps1
# This script demonstrates how to interact with VxRail API using PowerShell

# Ignore SSL certificate validation
# Note: In production, you should use proper certificate validation
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

# Force TLS 1.2
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

function Get-VxRailSystemInfo {
    param(
        [Parameter(Mandatory=$true)]
        [string]$VxRailIP,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [SecureString]$SecurePassword
    )

    # Convert SecureString password to plain text for API authentication
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
    $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

    # Construct API URL
    $baseUrl = "https://$VxRailIP/rest/vxm"
    $systemInfoUrl = "$baseUrl/v3/system"

    # Create basic authentication header
    $base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(("{0}:{1}" -f $Username, $Password)))
    $headers = @{
        Authorization = "Basic $base64AuthInfo"
        Accept = "application/json"
    }

    try {
        # Make API request
        $response = Invoke-RestMethod -Uri $systemInfoUrl -Headers $headers -Method Get -ContentType "application/json"

        # Format and display the results
        Write-Host "`n=== VxRail System Information ===" -ForegroundColor Green
        Write-Host "Version: $($response.version)"
        Write-Host "Health: $($response.health)"

        if ($response.cluster_info) {
            Write-Host "`nCluster Information:" -ForegroundColor Cyan
            Write-Host "Cluster Name: $($response.cluster_info.cluster_name)"
            Write-Host "Datacenter: $($response.cluster_info.datacenter_name)"
            Write-Host "vCenter Version: $($response.cluster_info.vc_version)"
        }

        if ($response.network) {
            Write-Host "`nNetwork Information:" -ForegroundColor Cyan
            Write-Host "Network Mode: $($response.network.mode)"
        }

        # Return the full response object for further processing if needed
        return $response

    } catch {
        Write-Host "`nError accessing VxRail API:" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Write-Host "`nResponse:" -ForegroundColor Red
        Write-Host $_.ErrorDetails.Message
    }
}

# Example usage:
# Get credentials interactively
Write-Host "`nEnter VxRail Manager credentials" -ForegroundColor Yellow
$vxrailIP = Read-Host "Enter VxRail Manager IP or hostname"
$username = Read-Host "Enter username"
$securePassword = Read-Host "Enter password" -AsSecureString

# Call the function
$systemInfo = Get-VxRailSystemInfo -VxRailIP $vxrailIP -Username $username -SecurePassword $securePassword

# To see the raw JSON response:
# $systemInfo | ConvertTo-Json -Depth 10
