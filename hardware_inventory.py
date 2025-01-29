#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import urllib3
import json
from getpass import getpass
from datetime import datetime

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

def make_api_request(base_url, endpoint, auth):
    """
    Make an API request to VxRail Manager.
    
    Args:
        base_url (str): Base URL of the VxRail Manager
        endpoint (str): API endpoint to call
        auth (HTTPBasicAuth): Authentication object
    
    Returns:
        dict: JSON response if successful, None if failed
    """
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            auth=auth,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {endpoint}: {str(e)}")
        return None

def get_hardware_inventory(vxrail_ip, username, password):
    """
    Collect comprehensive hardware inventory from the VxRail cluster.
    
    Args:
        vxrail_ip (str): VxRail Manager IP address or hostname
        username (str): Authentication username
        password (str): Authentication password
    
    Returns:
        dict: Hardware inventory information
    """
    base_url = f"https://{vxrail_ip}/rest/vxm"
    auth = HTTPBasicAuth(username, password)
    
    inventory = {
        'timestamp': datetime.now().isoformat(),
        'hosts': [],
        'chassis': [],
        'disks': []
    }
    
    # Get host information (using v7 API for most recent features)
    hosts_data = make_api_request(base_url, '/v7/hosts', auth)
    if hosts_data:
        inventory['hosts'] = hosts_data
        print(f"Found {len(hosts_data)} hosts")
    
    # Get chassis information (using v4 API for most comprehensive data)
    chassis_data = make_api_request(base_url, '/v4/chassis', auth)
    if chassis_data:
        inventory['chassis'] = chassis_data
        print(f"Found {len(chassis_data)} chassis")
    
    # Get disk information
    disks_data = make_api_request(base_url, '/v1/disks', auth)
    if disks_data:
        inventory['disks'] = disks_data
        print(f"Found {len(disks_data)} disks")
    
    return inventory

def save_inventory_to_file(inventory):
    """
    Save the inventory data to a JSON file.
    
    Args:
        inventory (dict): Hardware inventory data
    """
    filename = f"vxrail_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(inventory, f, indent=2)
        print(f"\nInventory saved to {filename}")
    except Exception as e:
        print(f"Error saving inventory to file: {str(e)}")

def display_inventory_summary(inventory):
    """
    Display a summary of the collected hardware inventory.
    
    Args:
        inventory (dict): Hardware inventory data
    """
    print("\n=== VxRail Hardware Inventory Summary ===")
    print(f"Inventory collected at: {inventory['timestamp']}")
    
    # Host summary
    if inventory['hosts']:
        print("\nHosts:")
        for host in inventory['hosts']:
            print(f"\n- Host {host.get('host_name', 'N/A')}:")
            print(f"  Serial Number: {host.get('serial_number', 'N/A')}")
            print(f"  Model: {host.get('model', 'N/A')}")
            print(f"  Management IP: {host.get('management_ip', 'N/A')}")
            print(f"  Health Status: {host.get('health', 'N/A')}")
    
    # Chassis summary
    if inventory['chassis']:
        print("\nChassis:")
        for chassis in inventory['chassis']:
            print(f"\n- Chassis {chassis.get('id', 'N/A')}:")
            print(f"  Serial Number: {chassis.get('serial_number', 'N/A')}")
            print(f"  Model: {chassis.get('model', 'N/A')}")
            print(f"  Health Status: {chassis.get('health', 'N/A')}")
    
    # Disk summary
    if inventory['disks']:
        print("\nDisks Summary:")
        disk_types = {}
        total_capacity = 0
        for disk in inventory['disks']:
            disk_type = disk.get('disk_type', 'Unknown')
            disk_types[disk_type] = disk_types.get(disk_type, 0) + 1
            capacity = disk.get('capacity', 0)
            if isinstance(capacity, (int, float)):
                total_capacity += capacity
        
        print(f"  Total number of disks: {len(inventory['disks'])}")
        print("  Disk types distribution:")
        for disk_type, count in disk_types.items():
            print(f"    - {disk_type}: {count}")
        print(f"  Total raw capacity: {total_capacity / (1024*1024*1024):.2f} TB")

def main():
    """
    Main function that orchestrates the hardware inventory collection.
    """
    # Get authentication parameters from user
    vxrail_ip, username, password = get_authentication_params()
    
    print("\nCollecting hardware inventory...")
    
    # Get hardware inventory
    inventory = get_hardware_inventory(vxrail_ip, username, password)
    
    if inventory:
        # Save inventory to file
        save_inventory_to_file(inventory)
        
        # Display inventory summary
        display_inventory_summary(inventory)
    else:
        print("Failed to collect hardware inventory.")

if __name__ == "__main__":
    main()
