#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import urllib3
import json
from datetime import datetime
import sys
from getpass import getpass
import time

# Disable SSL warnings - in production, use proper certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_auth_params():
    """Get VxRail Manager connection parameters from user"""
    vxrail_ip = input("VxRail Manager IP/hostname: ")
    username = input("Username: ")
    password = getpass("Password: ")
    return vxrail_ip, username, password

def make_api_request(base_url, endpoint, auth, method='GET', data=None):
    """
    Make an API request to VxRail Manager
    
    Args:
        base_url (str): Base URL of VxRail Manager
        endpoint (str): API endpoint
        auth (HTTPBasicAuth): Authentication object
        method (str): HTTP method (GET/POST)
        data (dict): Data for POST requests
    """
    try:
        url = f"{base_url}{endpoint}"
        if method == 'GET':
            response = requests.get(url, auth=auth, verify=False, timeout=30)
        else:
            response = requests.post(url, auth=auth, verify=False, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {endpoint}: {str(e)}")
        return None

def check_system_health(base_url, auth):
    """Check overall system health"""
    print("\nChecking system health...")
    system_info = make_api_request(base_url, "/v3/system", auth)
    
    if system_info:
        health_status = system_info.get('health', 'UNKNOWN')
        print(f"System Health: {health_status}")
        return system_info
    return None

def check_hosts_health(base_url, auth):
    """Check health of all hosts"""
    print("\nChecking hosts health...")
    hosts = make_api_request(base_url, "/v7/hosts", auth)
    
    if not hosts:
        return None
    
    host_summary = []
    for host in hosts:
        host_info = {
            'hostname': host.get('hostname', 'N/A'),
            'health': host.get('health', 'UNKNOWN'),
            'power_status': host.get('power_status', 'UNKNOWN'),
            'serial_number': host.get('serial_number', 'N/A')
        }
        host_summary.append(host_info)
        print(f"Host {host_info['hostname']}: Health={host_info['health']}, Power={host_info['power_status']}")
    
    return host_summary

def perform_system_precheck(base_url, auth):
    """Perform system pre-check"""
    print("\nPerforming system pre-check...")
    
    # Initiate pre-check
    precheck_response = make_api_request(base_url, "/v1/system/precheck", auth, 'POST')
    if not precheck_response:
        return None
    
    request_id = precheck_response.get('request_id')
    if not request_id:
        print("Failed to get request ID for pre-check")
        return None
    
    # Monitor pre-check progress
    max_attempts = 30
    for attempt in range(max_attempts):
        status = make_api_request(base_url, f"/v1/requests/{request_id}", auth)
        if not status:
            continue
            
        state = status.get('state', '')
        if state == 'COMPLETED':
            print("Pre-check completed successfully")
            return status
        elif state == 'FAILED':
            print("Pre-check failed")
            return status
            
        print(f"Pre-check in progress... ({state})")
        time.sleep(10)  # Wait 10 seconds before next check
    
    print("Pre-check timed out")
    return None

def check_support_status(base_url, auth):
    """Check support configuration"""
    print("\nChecking support configuration...")
    support_info = make_api_request(base_url, "/v1/support/account", auth)
    
    if support_info:
        print(f"Support Account Status: {support_info.get('status', 'UNKNOWN')}")
    return support_info

def generate_health_report(system_info, host_summary, precheck_results, support_info):
    """Generate a health report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_health': system_info.get('health') if system_info else 'UNKNOWN',
        'system_version': system_info.get('version') if system_info else 'UNKNOWN',
        'hosts': host_summary if host_summary else [],
        'precheck_results': precheck_results,
        'support_status': support_info.get('status') if support_info else 'UNKNOWN'
    }
    
    # Save report to file
    filename = f"vxrail_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nHealth report saved to {filename}")
    return report

def main():
    """Main function to run health check"""
    print("=== VxRail Health Check Utility ===")
    
    # Get authentication parameters
    vxrail_ip, username, password = get_auth_params()
    base_url = f"https://{vxrail_ip}/rest/vxm"
    auth = HTTPBasicAuth(username, password)
    
    # Perform health checks
    system_info = check_system_health(base_url, auth)
    host_summary = check_hosts_health(base_url, auth)
    precheck_results = perform_system_precheck(base_url, auth)
    support_info = check_support_status(base_url, auth)
    
    # Generate report
    generate_health_report(system_info, host_summary, precheck_results, support_info)

if __name__ == "__main__":
    main()
