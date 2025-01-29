#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import urllib3
import json
from getpass import getpass

# Disable SSL warnings - in production environment, proper SSL certificates should be used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_authentication_params():
    """
    Interactively collect authentication parameters from the user.
    Returns:
        tuple: VxRail Manager IP/hostname, username, and password
    """
    print("\n=== VxRail API Authentication ===")
    vxrail_ip = input("Enter VxRail Manager IP or hostname: ")
    username = input("Enter username: ")
    password = getpass("Enter password: ")  # getpass hides the password while typing
    return vxrail_ip, username, password

def get_system_info(vxrail_ip, username, password):
    """
    Retrieve system information from the VxRail cluster.
    
    Args:
        vxrail_ip (str): VxRail Manager IP address or hostname
        username (str): Authentication username
        password (str): Authentication password
    
    Returns:
        dict: System information if successful, None if failed
    """
    # Construct the base URL for the API
    base_url = f"https://{vxrail_ip}/rest/vxm"
    
    try:
        # Make API request to get system information
        # We're using v3/system endpoint as it provides comprehensive system information
        response = requests.get(
            f"{base_url}/v3/system",
            auth=HTTPBasicAuth(username, password),
            verify=False,  # Disable SSL verification - don't use this in production!
            timeout=30  # Set timeout to 30 seconds
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Return the JSON response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"\nError accessing VxRail API: {str(e)}")
        return None

def display_system_info(system_info):
    """
    Display the system information in a readable format.
    
    Args:
        system_info (dict): System information returned from the API
    """
    if not system_info:
        print("\nNo system information available.")
        return

    print("\n=== VxRail System Information ===")
    
    # Extract and display relevant information
    try:
        print(f"System Version: {system_info.get('version', 'N/A')}")
        print(f"Health Status: {system_info.get('health', 'N/A')}")
        
        # Display cluster information if available
        if 'cluster_info' in system_info:
            cluster = system_info['cluster_info']
            print(f"\nCluster Name: {cluster.get('cluster_name', 'N/A')}")
            print(f"Datacenter Name: {cluster.get('datacenter_name', 'N/A')}")
            print(f"vCenter Version: {cluster.get('vc_version', 'N/A')}")
        
        # Display network information if available
        if 'network' in system_info:
            network = system_info['network']
            print(f"\nNetwork Mode: {network.get('mode', 'N/A')}")
            
        print("\nFor full system information, see the raw JSON response below:")
        print(json.dumps(system_info, indent=2))
        
    except Exception as e:
        print(f"\nError parsing system information: {str(e)}")

def main():
    """
    Main function that orchestrates the VxRail API interaction.
    """
    # Get authentication parameters from user
    vxrail_ip, username, password = get_authentication_params()
    
    print("\nConnecting to VxRail Manager...")
    
    # Get system information
    system_info = get_system_info(vxrail_ip, username, password)
    
    # Display the results
    display_system_info(system_info)

if __name__ == "__main__":
    main()
