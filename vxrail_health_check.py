#!/usr/bin/env python3
"""
VxRail Health Check Script
This script connects to a VxRail Manager and retrieves the health status of various components
including cluster health, host health, and storage health.

Required Python packages:
- requests
- urllib3
"""

import requests
import urllib3
import json
import sys
from typing import Dict, Any, Optional
from base64 import b64encode
from datetime import datetime

# Disable SSL warnings - Use this only in test environments
# In production, you should properly handle SSL certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_basic_auth_header(username: str, password: str) -> Dict[str, str]:
    """
    Create HTTP Basic Authentication header.
    
    Args:
        username: VxRail Manager username
        password: VxRail Manager password
    
    Returns:
        Dictionary containing the Authorization header
    """
    credentials = f"{username}:{password}"
    encoded_credentials = b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {"Authorization": f"Basic {encoded_credentials}"}

def make_api_request(base_url: str, endpoint: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Make HTTP GET request to VxRail API endpoint with error handling.
    
    Args:
        base_url: Base URL of the VxRail Manager
        endpoint: API endpoint to call
        headers: Request headers including authentication
    
    Returns:
        JSON response if successful, None if failed
    """
    try:
        # Construct full URL and make request
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 401:
                print(f"Error: Authentication failed. Please check your credentials.")
            elif e.response.status_code == 404:
                print(f"Error: Endpoint {endpoint} not found.")
            else:
                print(f"HTTP Error: {e}")
        elif isinstance(e, requests.exceptions.ConnectionError):
            print(f"Error: Could not connect to VxRail Manager. Please check the URL and network connection.")
        elif isinstance(e, requests.exceptions.Timeout):
            print(f"Error: Request timed out. The server took too long to respond.")
        else:
            print(f"Error: An unexpected error occurred: {e}")
        return None

def check_cluster_health(base_url: str, headers: Dict[str, str]) -> bool:
    """
    Check the overall cluster health status.
    
    Args:
        base_url: Base URL of the VxRail Manager
        headers: Request headers including authentication
    
    Returns:
        True if cluster is healthy, False otherwise
    """
    print("\nChecking cluster health...")
    response = make_api_request(base_url, "/rest/vxm/v1/cluster", headers)
    
    if response:
        # Extract and display relevant health information
        cluster_name = response.get('cluster_name', 'Unknown')
        health_status = response.get('health', 'Unknown')
        
        print(f"Cluster Name: {cluster_name}")
        print(f"Health Status: {health_status}")
        
        return health_status.lower() == 'healthy'
    return False

def check_hosts_health(base_url: str, headers: Dict[str, str]) -> bool:
    """
    Check the health status of all hosts in the cluster.
    
    Args:
        base_url: Base URL of the VxRail Manager
        headers: Request headers including authentication
    
    Returns:
        True if all hosts are healthy, False otherwise
    """
    print("\nChecking hosts health...")
    response = make_api_request(base_url, "/rest/vxm/v7/hosts", headers)
    
    if not response:
        return False
    
    all_healthy = True
    for host in response:
        hostname = host.get('hostname', 'Unknown')
        health_status = host.get('health', 'Unknown')
        power_status = host.get('power_status', 'Unknown')
        
        print(f"\nHost: {hostname}")
        print(f"Health Status: {health_status}")
        print(f"Power Status: {power_status}")
        
        if health_status.lower() != 'healthy':
            all_healthy = False
    
    return all_healthy

def check_storage_health(base_url: str, headers: Dict[str, str]) -> bool:
    """
    Check the health status of storage components.
    
    Args:
        base_url: Base URL of the VxRail Manager
        headers: Request headers including authentication
    
    Returns:
        True if storage is healthy, False otherwise
    """
    print("\nChecking storage health...")
    response = make_api_request(base_url, "/rest/vxm/v1/disks", headers)
    
    if not response:
        return False
    
    all_healthy = True
    for disk in response:
        disk_sn = disk.get('sn', 'Unknown')
        health_status = disk.get('health', 'Unknown')
        disk_type = disk.get('disk_type', 'Unknown')
        
        print(f"\nDisk SN: {disk_sn}")
        print(f"Type: {disk_type}")
        print(f"Health Status: {health_status}")
        
        if health_status.lower() != 'healthy':
            all_healthy = False
    
    return all_healthy

def main():
    """
    Main function to run the VxRail health check.
    Prompts for credentials and performs health checks on various components.
    """
    # Configuration
    vxrail_host = input("Enter VxRail Manager IP or hostname: ")
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    # Construct base URL
    base_url = f"https://{vxrail_host}"
    
    # Create authentication headers
    headers = create_basic_auth_header(username, password)
    headers["Content-Type"] = "application/json"
    
    print("\nStarting VxRail Health Check...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # Perform health checks
    cluster_healthy = check_cluster_health(base_url, headers)
    hosts_healthy = check_hosts_health(base_url, headers)
    storage_healthy = check_storage_health(base_url, headers)
    
    # Print summary
    print("\nHealth Check Summary:")
    print("-" * 50)
    print(f"Cluster Health: {'✓ Healthy' if cluster_healthy else '✗ Unhealthy'}")
    print(f"Hosts Health: {'✓ Healthy' if hosts_healthy else '✗ Unhealthy'}")
    print(f"Storage Health: {'✓ Healthy' if storage_healthy else '✗ Unhealthy'}")
    
    # Overall system status
    system_healthy = all([cluster_healthy, hosts_healthy, storage_healthy])
    print("\nOverall System Status:", 
          "✓ HEALTHY" if system_healthy else "✗ ATTENTION REQUIRED")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
