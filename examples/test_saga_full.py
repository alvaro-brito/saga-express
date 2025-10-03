#!/usr/bin/env python3
"""
Script de teste completo com serviços mock rodando
"""
import requests
import json
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

def create_or_get_saga_configuration():
    """Create a test saga configuration with Docker service URLs or get existing one"""
    print_section("Creating/Getting Saga Configuration (Docker)")
    
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
            
            # Fallback to localhost configuration if available
            for saga in sagas:
                if saga['name'] == "test-order-saga-localhost" and saga['status'] == 'active':
                    print_result(True, f"Found localhost saga configuration with ID: {saga['id']} (may not work in Docker)")
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
        "description": "Test saga for order processing with Docker services",
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

def test_saga_execution(saga_id):
    """Test saga execution with mock services"""
    print_section(f"Testing Full Saga Execution {saga_id}")
    
    test_data = {
        "saga_configuration_id": saga_id,
        "input_data": {
            "order_id": "ORDER-FULL-TEST",
            "customer_id": "CUST-12345",
            "customer_name": "Jane Doe",
            "customer_email": "jane.doe@example.com",
            "payment_method": "credit_card",
            "items": [
                {
                    "item_id": "ITEM-A",
                    "name": "Product A",
                    "quantity": 3,
                    "price": 75.0
                },
                {
                    "item_id": "ITEM-B",
                    "name": "Product B",
                    "quantity": 2,
                    "price": 125.0
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
        
        print("Sending test request with mock services...")
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
            print(f"\n  Step Details:")
            
            for step in execution.get('steps', []):
                status_icon = "✓" if step['status'] == 'completed' else "✗"
                print(f"    {status_icon} {step['step_name']}: {step['status']}")
                if step.get('error_message'):
                    print(f"       Error: {step['error_message']}")
                if step.get('response_data'):
                    print(f"       Response: {json.dumps(step['response_data'], indent=10)[:100]}...")
            
            return execution['id'], execution['status']
        else:
            print_result(False, f"Failed to execute saga: {response.text}")
            return None, None
    except Exception as e:
        print_result(False, f"Error executing saga: {str(e)}")
        return None, None

def main():
    print("\n" + "="*60)
    print("  SAGA EXPRESS - Full Integration Test")
    print("="*60)
    
    # Verify mock services are running
    print_section("Verifying Mock Services")
    services = {
        "Order Service": "http://localhost:8001/",
        "Inventory Service": "http://localhost:8002/",
        "Payment Service": "http://localhost:8003/"
    }
    
    all_running = True
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print_result(True, f"{name} is running")
            else:
                print_result(False, f"{name} returned status {response.status_code}")
                all_running = False
        except Exception as e:
            print_result(False, f"{name} is not accessible: {str(e)}")
            all_running = False
    
    if not all_running:
        print("\n❌ Not all mock services are running. Please start them first.")
        sys.exit(1)
    
    # Create or get saga configuration
    saga_id = create_or_get_saga_configuration()
    if not saga_id:
        print("\n❌ Failed to create/get saga configuration")
        sys.exit(1)
    
    # Test execution
    execution_id, status = test_saga_execution(saga_id)
    
    if execution_id:
        if status == "completed":
            print_section("✓ SUCCESS - Full Saga Execution Completed")
            print("All steps were executed successfully!")
        elif status == "rolled_back":
            print_section("⚠️  ROLLBACK - Saga was rolled back")
            print("Some steps failed and rollback was executed.")
        else:
            print_section(f"Status: {status}")
    
    print("\n" + "="*60)
    print("  Full Integration Test Completed")
    print("="*60)

if __name__ == "__main__":
    main()
