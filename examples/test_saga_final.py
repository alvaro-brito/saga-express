#!/usr/bin/env python3
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

def test_full_saga():
    # First try to find the localhost-compatible saga configuration
    saga_id = None
    saga_name = None
    
    try:
        response = requests.get(f"{API_URL}/saga-configurations/")
        if response.status_code == 200:
            sagas = response.json()
            # Look for the localhost-compatible configuration first
            for saga in sagas:
                if saga['name'] == "test-order-saga-localhost" and saga['status'] == 'active':
                    saga_id = saga['id']
                    saga_name = saga['name']
                    print(f"✓ Found localhost-compatible saga configuration ID: {saga_id} (name: {saga_name})")
                    break
            
            # If not found, look for any active saga with localhost in the name
            if not saga_id:
                for saga in sagas:
                    if "localhost" in saga['name'] and saga['status'] == 'active':
                        saga_id = saga['id']
                        saga_name = saga['name']
                        print(f"✓ Found existing localhost saga configuration ID: {saga_id} (name: {saga_name})")
                        break
    except Exception as e:
        print(f"Error checking existing sagas: {str(e)}")
    
    # If no existing saga found, create a localhost-compatible one
    if not saga_id:
        saga_name = "test-order-saga-localhost"
        
        with open("examples/test_saga_localhost.yaml", "r") as f:
            yaml_content = f.read()
        
        # Create saga
        saga_data = {
            "name": saga_name,
            "version": "1.0.0",
            "description": "Test saga for localhost environment",
            "yaml_content": yaml_content
        }
        
        response = requests.post(f"{API_URL}/saga-configurations/", json=saga_data)
        if response.status_code != 201:
            print(f"Failed to create saga: {response.text}")
            return False
        
        saga_id = response.json()['id']
        print(f"✓ Created localhost-compatible saga configuration ID: {saga_id}")
    
    # Test execution
    test_data = {
        "saga_configuration_id": saga_id,
        "input_data": {
            "order_id": "ORDER-FINAL-TEST",
            "customer_id": "CUST-999",
            "customer_name": "Test User",
            "customer_email": "test@example.com",
            "payment_method": "credit_card",
            "items": [
                {"item_id": "ITEM-X", "name": "Product X", "quantity": 2, "price": 50.0},
                {"item_id": "ITEM-Y", "name": "Product Y", "quantity": 1, "price": 100.0}
            ]
        }
    }
    
    # Show services that will be accessed
    print("\n" + "="*60)
    print("  SERVICES TO BE ACCESSED")
    print("="*60)
    
    # Get saga configuration to show endpoints
    try:
        config_response = requests.get(f"{API_URL}/saga-configurations/{saga_id}")
        if config_response.status_code == 200:
            config = config_response.json()
            yaml_content = config['yaml_content']
            
            # Parse YAML to extract endpoints
            import yaml
            saga_config = yaml.safe_load(yaml_content)
            
            step_num = 1
            for execution in saga_config.get('executions', []):
                step_name = execution.get('name', f'step-{step_num}')
                step_type = execution.get('type', 'unknown')
                
                if step_type == 'api':
                    endpoint = execution.get('endpoint', {})
                    url = endpoint.get('url', 'N/A')
                    method = endpoint.get('method', 'GET')
                    print(f"  {step_num}. {step_name} ({step_type.upper()})")
                    print(f"     {method} {url}")
                elif step_type == 'kafka':
                    endpoint = execution.get('endpoint', {})
                    topic = endpoint.get('topic', 'N/A')
                    print(f"  {step_num}. {step_name} ({step_type.upper()})")
                    print(f"     Topic: {topic}")
                
                step_num += 1
                
        print("="*60)
    except Exception as e:
        print(f"Could not parse saga configuration: {e}")
        print("="*60)
    
    print("Executing saga...")
    response = requests.post(f"{API_URL}/saga-executions/test", json=test_data, timeout=60)
    
    if response.status_code != 200:
        print(f"Failed to execute saga: {response.text}")
        return False
    
    execution = response.json()
    print(f"\n{'='*60}")
    print(f"  SAGA EXECUTION RESULT")
    print(f"{'='*60}")
    print(f"Execution ID: {execution['id']}")
    print(f"Status: {execution['status']}")
    print(f"Steps: {len(execution.get('steps', []))}")
    print(f"\nStep Details:")
    
    for step in execution.get('steps', []):
        status_icon = "✓" if step['status'] == 'completed' else "✗"
        print(f"  {status_icon} {step['step_name']}: {step['status']}")
        if step.get('error_message'):
            print(f"     Error: {step['error_message']}")
    
    if execution['status'] == 'completed':
        print(f"\n{'='*60}")
        print("  ✓ SUCCESS - All steps completed!")
        print(f"{'='*60}")
        return True
    else:
        print(f"\n{'='*60}")
        print(f"  Status: {execution['status']}")
        print(f"{'='*60}")
        return False

if __name__ == "__main__":
    success = test_full_saga()
    sys.exit(0 if success else 1)
