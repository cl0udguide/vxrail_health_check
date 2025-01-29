#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import urllib3
import json
from getpass import getpass
import time

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

def get_basic_health(base_url, auth):
    """
    Get basic health status of the VxRail system.
    
    Args:
        base_url (str): Base URL of the VxRail API
        auth (HTTPBasicAuth): Authentication object
    
    Returns:
        dict: Health information if successful, None if failed
    """
    try:
        response = requests.get(
            f"{base_url}/v3/system",
            auth=auth,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        system_info = response.json()
        return {
            'health': system_info.get('health'),
            'state': system_info.get('operational_status'),
            'components': system_info.get('health_components', [])
        }
    except requests.exceptions.RequestException as e:
        print(f"\nError getting basic health status: {str(e)}")
        return None

def perform_health_precheck(base_url, auth):
    """
    Perform a detailed health pre-check of the system.
    
    Args:
        base_url (str): Base URL of the VxRail API
        auth (HTTPBasicAuth): Authentication object
    
    Returns:
        dict: Pre-check results if successful, None if failed
    """
    try:
        # Initiate the pre-check
        response = requests.post(
            f"{base_url}/v1/lcm/precheck",
            auth=auth,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        request_id = response.json().get('request_id')
        
        if not request_id:
            print("Failed to get request ID for health pre-check")
            return None
            
        # Poll for pre-check completion
        print("\nHealth pre-check initiated. Waiting for results...")
        while True:
            status_response = requests.get(
                f"{base_url}/v1/requests/{request_id}",
                auth=auth,
                verify=False,
                timeout=30
            )
            status_response.raise_for_status()
            status_data = status_response.json()
            
            state = status_data.get('state', '')
            
            if state == 'COMPLETED':
                # Get the detailed results
                results_response = requests.get(
                    f"{base_url}/v1/system/prechecks/{request_id}/result",
                    auth=auth,
                    verify=False,
                    timeout=30
                )
                results_response.raise_for_status()
                return results_response.json()
                
            elif state == 'FAILED':
                print(f"\nPre-check failed: {status_data.get('error', 'Unknown error')}")
                return None
                
            print(".", end="", flush=True)
            time.sleep(5)  # Wait 5 seconds before checking again
            
    except requests.exceptions.RequestException as e:
        print(f"\nError performing health pre-check: {str(e)}")
        return None

def display_health_info(basic_health, precheck_results):
    """
    Display health information in a readable format.
    
    Args:
        basic_health (dict): Basic health information
        precheck_results (dict): Detailed pre-check results
    """
    print("\n=== VxRail System Health Status ===")
    
    if basic_health:
        print(f"\nBasic Health Status:")
        print(f"Overall Health: {basic_health.get('health', 'N/A')}")
        print(f"Operational State: {basic_health.get('state', 'N/A')}")
        
        print("\nComponent Health:")
        for component in basic_health.get('components', []):
            print(f"- {component.get('name', 'Unknown')}: {component.get('health', 'N/A')}")
    
    if precheck_results:
        print("\nDetailed Health Pre-check Results:")
        
        # Display each check result
        for check in precheck_results.get('data', {}).get('check_list', []):
            status = check.get('status', 'Unknown')
            status_symbol = "✓" if status == "PASSED" else "✗"
            
            print(f"\n{status_symbol} {check.get('name', 'Unknown Check')}:")
            print(f"   Status: {status}")
            
            if status != "PASSED":
                print(f"   Message: {check.get('message', 'No message provided')}")
                
            # Display sub-checks if available
            for sub_check in check.get('sub_checks', []):
                sub_status = sub_check.get('status', 'Unknown')
                sub_symbol = "✓" if sub_status == "PASSED" else "✗"
                print(f"   {sub_symbol} {sub_check.get('name', 'Unknown Sub-check')}: {sub_status}")
                
                if sub_status != "PASSED":
                    print(f"      Message: {sub_check.get('message', 'No message provided')}")

def main():
    """
    Main function that orchestrates the health check process.
    """
    # Get authentication parameters
    vxrail_ip, username, password = get_authentication_params()
    
    # Prepare base URL and authentication
    base_url = f"https://{vxrail_ip}/rest/vxm"
    auth = HTTPBasicAuth(username, password)
    
    print("\nChecking VxRail system health...")
    
    # Get basic health status
    basic_health = get_basic_health(base_url, auth)
    
    # Perform detailed health pre-check
    print("\nInitiating detailed health pre-check...")
    precheck_results = perform_health_precheck(base_url, auth)
    
    # Display results
    display_health_info(basic_health, precheck_results)

if __name__ == "__main__":
    main()
