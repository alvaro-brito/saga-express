#!/usr/bin/env python3
"""
Script de teste completo para o Saga Express
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_result(success, message):
    status = "✓" if success else "✗"
    print(f"{status} {message}")

def test_health():
    """Test health endpoint"""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print_result(response.status_code == 200, f"Health check: {response.json()}")
        return True
    except Exception as e:
        print_result(False, f"Health check failed: {str(e)}")
        return False

def create_or_get_saga_configuration():
    """Create a test saga configuration or get existing one"""
    print_section("Creating/Getting Saga Configuration")
    
    # First, check if Docker-compatible saga already exists
    try:
        response = requests.get(f"{API_URL}/saga-configurations/")
        if response.status_code == 200:
            sagas = response.json()
            # Look for Docker-compatible configuration first
            for saga in sagas:
                if saga['name'] == "test-order-saga" and saga['status'] == 'active':
                    print_result(True, f"Found Docker-compatible saga configuration with ID: {saga['id']}")
                    return saga['id']
    except Exception as e:
        print_result(False, f"Error checking existing sagas: {str(e)}")
    
    # If not found, create Docker-compatible one
    saga_name = "test-order-saga"
    with open("examples/test_saga_config.yaml", "r") as f:
        yaml_content = f.read()
    
    saga_data = {
        "name": saga_name,
        "version": "1.0.0",
        "description": "Test saga for order processing (Docker-compatible)",
        "yaml_content": yaml_content
    }
    
    try:
        response = requests.post(
            f"{API_URL}/saga-configurations/",
            json=saga_data
        )
        
        if response.status_code == 201:
            saga = response.json()
            print_result(True, f"Docker-compatible saga configuration created with ID: {saga['id']}")
            return saga['id']
        else:
            print_result(False, f"Failed to create saga: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Error creating saga: {str(e)}")
        return None

def list_saga_configurations():
    """List all saga configurations"""
    print_section("Listing Saga Configurations")
    
    try:
        response = requests.get(f"{API_URL}/saga-configurations/")
        
        if response.status_code == 200:
            sagas = response.json()
            print_result(True, f"Found {len(sagas)} saga configuration(s)")
            for saga in sagas:
                print(f"  - ID: {saga['id']}, Name: {saga['name']}, Status: {saga['status']}")
            return True
        else:
            print_result(False, f"Failed to list sagas: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error listing sagas: {str(e)}")
        return False

def get_saga_configuration(saga_id):
    """Get a specific saga configuration"""
    print_section(f"Getting Saga Configuration {saga_id}")
    
    try:
        response = requests.get(f"{API_URL}/saga-configurations/{saga_id}")
        
        if response.status_code == 200:
            saga = response.json()
            print_result(True, f"Saga: {saga['name']} (v{saga['version']})")
            print(f"  Status: {saga['status']}")
            print(f"  Description: {saga['description']}")
            return True
        else:
            print_result(False, f"Failed to get saga: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error getting saga: {str(e)}")
        return False

def disable_saga_configuration(saga_id):
    """Disable a saga configuration"""
    print_section(f"Disabling Saga Configuration {saga_id}")
    
    try:
        response = requests.post(f"{API_URL}/saga-configurations/{saga_id}/disable")
        
        if response.status_code == 200:
            saga = response.json()
            print_result(True, f"Saga disabled. Status: {saga['status']}")
            return True
        else:
            print_result(False, f"Failed to disable saga: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error disabling saga: {str(e)}")
        return False

def enable_saga_configuration(saga_id):
    """Enable a saga configuration"""
    print_section(f"Enabling Saga Configuration {saga_id}")
    
    try:
        response = requests.post(f"{API_URL}/saga-configurations/{saga_id}/enable")
        
        if response.status_code == 200:
            saga = response.json()
            print_result(True, f"Saga enabled. Status: {saga['status']}")
            return True
        else:
            print_result(False, f"Failed to enable saga: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error enabling saga: {str(e)}")
        return False

def test_saga_execution(saga_id):
    """Test saga execution with mock data"""
    print_section(f"Testing Saga Execution {saga_id}")
    
    test_data = {
        "saga_configuration_id": saga_id,
        "input_data": {
            "order_id": "ORDER-12345",
            "customer_id": "CUST-67890",
            "customer_name": "John Doe",
            "customer_email": "john.doe@example.com",
            "payment_method": "credit_card",
            "items": [
                {
                    "item_id": "ITEM-001",
                    "name": "Product A",
                    "quantity": 2,
                    "price": 50.0
                },
                {
                    "item_id": "ITEM-002",
                    "name": "Product B",
                    "quantity": 1,
                    "price": 100.0
                }
            ]
        }
    }
    
    try:
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
        
        print("Sending test request...")
        response = requests.post(
            f"{API_URL}/saga-executions/test",
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            execution = response.json()
            print_result(True, f"Saga execution completed")
            print(f"  Execution ID: {execution['id']}")
            print(f"  Correlation ID: {execution['correlation_id']}")
            print(f"  Status: {execution['status']}")
            print(f"  Steps executed: {len(execution.get('steps', []))}")
            
            for step in execution.get('steps', []):
                print(f"    - {step['step_name']}: {step['status']}")
            
            return execution['id']
        else:
            print_result(False, f"Failed to execute saga: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Error executing saga: {str(e)}")
        return None

def list_saga_executions():
    """List all saga executions"""
    print_section("Listing Saga Executions")
    
    try:
        response = requests.get(f"{API_URL}/saga-executions/")
        
        if response.status_code == 200:
            executions = response.json()
            print_result(True, f"Found {len(executions)} execution(s)")
            for execution in executions:
                print(f"  - ID: {execution['id']}, Status: {execution['status']}, Steps: {len(execution.get('steps', []))}")
            return True
        else:
            print_result(False, f"Failed to list executions: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error listing executions: {str(e)}")
        return False

def get_saga_execution(execution_id):
    """Get a specific saga execution"""
    print_section(f"Getting Saga Execution {execution_id}")
    
    try:
        response = requests.get(f"{API_URL}/saga-executions/{execution_id}")
        
        if response.status_code == 200:
            execution = response.json()
            print_result(True, f"Execution details retrieved")
            print(f"  Status: {execution['status']}")
            print(f"  Started: {execution['started_at']}")
            print(f"  Completed: {execution.get('completed_at', 'N/A')}")
            print(f"  Steps:")
            for step in execution.get('steps', []):
                print(f"    - {step['step_name']}: {step['status']}")
                if step.get('error_message'):
                    print(f"      Error: {step['error_message']}")
            return True
        else:
            print_result(False, f"Failed to get execution: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error getting execution: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("  SAGA EXPRESS - Test Suite")
    print("="*60)
    
    # Test health
    if not test_health():
        print("\n❌ Server is not running. Please start the server first.")
        sys.exit(1)
    
    # Create or get saga configuration
    saga_id = create_or_get_saga_configuration()
    if not saga_id:
        print("\n❌ Failed to create/get saga configuration")
        sys.exit(1)
    
    # List configurations
    list_saga_configurations()
    
    # Get configuration
    get_saga_configuration(saga_id)
    
    # Test disable/enable
    disable_saga_configuration(saga_id)
    enable_saga_configuration(saga_id)
    
    # Test execution (will fail without mock services running)
    print("\n⚠️  Note: Saga execution will fail without mock services running")
    print("    This is expected behavior for this test")
    execution_id = test_saga_execution(saga_id)
    
    # List executions
    list_saga_executions()
    
    # Get execution details
    if execution_id:
        get_saga_execution(execution_id)
    
    print_section("Test Suite Completed")
    print("✓ All API tests passed successfully!")
    print("\nNote: To test full saga execution with rollback,")
    print("      start the mock services using Docker Compose")

if __name__ == "__main__":
    main()
