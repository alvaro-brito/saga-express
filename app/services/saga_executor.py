import yaml
import httpx
import uuid
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from kafka import KafkaProducer
import json

from app.models import (
    SagaConfiguration,
    SagaExecution,
    SagaExecutionStatus,
    SagaExecutionStep,
    SagaExecutionStepStatus
)
from app.core.config import settings


class SagaExecutor:
    """Executes SAGA workflows based on YAML configuration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.context: Dict[str, Any] = {}
        self.kafka_producer: Optional[KafkaProducer] = None
    
    def _get_kafka_producer(self) -> KafkaProducer:
        """Get or create Kafka producer"""
        if self.kafka_producer is None:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
        return self.kafka_producer
    
    def _interpolate_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Interpolate variables in value using context"""
        if not isinstance(value, str):
            return value
        
        # Check if the entire value is a single variable reference
        single_var_pattern = r'^\$\{([^}]+)\}$'
        single_match = re.match(single_var_pattern, value)
        
        if single_match:
            var_path = single_match.group(1)
            
            # Handle special variables
            if var_path == "current_timestamp":
                return datetime.utcnow().isoformat()
            
            # Navigate through context using dot notation
            parts = var_path.split('.')
            current = context
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return value  # Return original if not found
            
            # Return the actual value (could be dict, list, etc.)
            return current
        
        # Pattern to match ${variable.path} for string interpolation
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_path = match.group(1)
            
            # Handle special variables
            if var_path == "current_timestamp":
                return datetime.utcnow().isoformat()
            
            # Navigate through context using dot notation
            parts = var_path.split('.')
            current = context
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return match.group(0)  # Return original if not found
            
            return str(current)
        
        result = re.sub(pattern, replace_var, value)
        return result
    
    def _interpolate_dict(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively interpolate all values in a dictionary"""
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._interpolate_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._interpolate_dict(item, context) if isinstance(item, dict)
                    else self._interpolate_value(item, context)
                    for item in value
                ]
            else:
                result[key] = self._interpolate_value(value, context)
        return result
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string"""
        # Handle compound conditions first
        if "&&" in condition:
            conditions = condition.split("&&")
            return all(self._evaluate_condition(c.strip(), context) for c in conditions)
        elif "||" in condition:
            conditions = condition.split("||")
            return any(self._evaluate_condition(c.strip(), context) for c in conditions)
        
        # Simple condition evaluation
        # Replace variables in condition
        interpolated = self._interpolate_value(condition, context)
        
        # Handle simple comparisons
        if "==" in interpolated:
            left, right = interpolated.split("==", 1)
            left = left.strip()
            right = right.strip()
            
            # Try to convert to numbers if possible
            try:
                left_num = float(left.strip('"').strip("'"))
                right_num = float(right.strip('"').strip("'"))
                return left_num == right_num
            except ValueError:
                # String comparison
                left = left.strip('"').strip("'")
                right = right.strip('"').strip("'")
                return left == right
        elif "!=" in interpolated:
            left, right = interpolated.split("!=", 1)
            left = left.strip()
            right = right.strip()
            
            # Try to convert to numbers if possible
            try:
                left_num = float(left.strip('"').strip("'"))
                right_num = float(right.strip('"').strip("'"))
                return left_num != right_num
            except ValueError:
                # String comparison
                left = left.strip('"').strip("'")
                right = right.strip('"').strip("'")
                return left != right
        
        # Default: try to evaluate as boolean
        return bool(interpolated)
    
    async def _execute_api_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any],
        execution: SagaExecution,
        step_name: str
    ) -> SagaExecutionStep:
        """Execute an API step"""
        step = SagaExecutionStep(
            saga_execution_id=execution.id,
            step_name=step_name,
            step_type="api",
            status=SagaExecutionStepStatus.RUNNING
        )
        self.db.add(step)
        self.db.commit()
        
        try:
            endpoint = step_config["endpoint"]
            url = self._interpolate_value(endpoint["url"], context)
            method = endpoint.get("method", "POST").upper()
            
            # Prepare headers
            headers = {}
            if "headers" in endpoint:
                headers = self._interpolate_dict(endpoint["headers"], context)
            
            # Prepare body
            body = None
            if "body" in step_config:
                body = self._interpolate_dict(step_config["body"], context)
            
            step.request_data = {
                "url": url,
                "method": method,
                "headers": headers,
                "body": body
            }
            self.db.commit()
            
            # Execute HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body
                )
                
                response_data = {
                    "status": response.status_code,
                    "body": response.json() if response.content else {}
                }
                
                step.response_data = response_data
                
                # Update context with response
                context[step_name] = {
                    "response": response_data
                }
                
                # Check success condition
                success_config = step_config.get("success", {})
                condition = success_config.get("condition", "response.status == 200")
                
                # Wrap condition variables in ${} for interpolation
                condition_for_eval = condition
                if "response." in condition and "${" not in condition:
                    # Replace response.xxx with ${response.xxx}
                    import re as re_module
                    condition_for_eval = re_module.sub(r'(response\.[a-zA-Z0-9_.]+)', r'${\1}', condition)
                
                interpolated_condition = self._interpolate_value(condition_for_eval, context[step_name])
                
                if self._evaluate_condition(condition_for_eval, context[step_name]):
                    # Extract values
                    if "extract" in success_config:
                        for key, path in success_config["extract"].items():
                            # Wrap path in ${} if needed
                            if not path.startswith("${"):
                                path_for_interp = "${" + path + "}"
                            else:
                                path_for_interp = path
                            value = self._interpolate_value(path_for_interp, context[step_name])
                            context[step_name][key] = value
                    
                    step.status = SagaExecutionStepStatus.COMPLETED
                else:
                    step.status = SagaExecutionStepStatus.FAILED
                    step.error_message = f"Condition not met: {condition} (interpolated: {interpolated_condition})"
                
                step.completed_at = datetime.utcnow()
                self.db.commit()
                
                return step
                
        except Exception as e:
            step.status = SagaExecutionStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.utcnow()
            self.db.commit()
            return step
    
    async def _execute_kafka_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any],
        execution: SagaExecution,
        step_name: str
    ) -> SagaExecutionStep:
        """Execute a Kafka step"""
        step = SagaExecutionStep(
            saga_execution_id=execution.id,
            step_name=step_name,
            step_type="kafka",
            status=SagaExecutionStepStatus.RUNNING
        )
        self.db.add(step)
        self.db.commit()
        
        try:
            endpoint = step_config["endpoint"]
            topic = self._interpolate_value(endpoint["topic"], context)
            partition_key = self._interpolate_value(endpoint.get("partition_key", ""), context)
            
            # Prepare headers
            headers = {}
            if "headers" in endpoint:
                headers = self._interpolate_dict(endpoint["headers"], context)
            
            # Prepare body
            body = self._interpolate_dict(step_config["body"], context)
            
            step.request_data = {
                "topic": topic,
                "partition_key": partition_key,
                "headers": headers,
                "body": body
            }
            self.db.commit()
            
            # Send to Kafka
            producer = self._get_kafka_producer()
            future = producer.send(
                topic=topic,
                key=partition_key if partition_key else None,
                value=body,
                headers=[(k, v.encode('utf-8')) for k, v in headers.items()]
            )
            
            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)
            
            response_data = {
                "topic": record_metadata.topic,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset,
                "ack_received": True
            }
            
            step.response_data = response_data
            
            # Update context
            context[step_name] = {
                "kafka": response_data
            }
            
            step.status = SagaExecutionStepStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            self.db.commit()
            
            return step
            
        except Exception as e:
            step.status = SagaExecutionStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.utcnow()
            self.db.commit()
            return step
    
    async def _rollback_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any],
        step_name: str
    ):
        """Execute rollback for a step"""
        if "rollback" not in step_config or step_config["rollback"] is None:
            return
        
        rollback_config = step_config["rollback"]
        rollback_type = rollback_config.get("type", "api")
        
        try:
            if rollback_type == "api":
                endpoint = rollback_config["endpoint"]
                url = self._interpolate_value(endpoint["url"], context)
                method = endpoint.get("method", "POST").upper()
                
                headers = {}
                if "headers" in endpoint:
                    headers = self._interpolate_dict(endpoint["headers"], context)
                
                body = None
                if "body" in rollback_config:
                    body = self._interpolate_dict(rollback_config["body"], context)
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=body
                    )
            
            elif rollback_type == "kafka":
                endpoint = rollback_config["endpoint"]
                topic = self._interpolate_value(endpoint["topic"], context)
                partition_key = self._interpolate_value(endpoint.get("partition_key", ""), context)
                
                headers = {}
                if "headers" in endpoint:
                    headers = self._interpolate_dict(endpoint["headers"], context)
                
                body = self._interpolate_dict(rollback_config["body"], context)
                
                producer = self._get_kafka_producer()
                producer.send(
                    topic=topic,
                    key=partition_key if partition_key else None,
                    value=body,
                    headers=[(k, v.encode('utf-8')) for k, v in headers.items()]
                )
                producer.flush()
        
        except Exception as e:
            # Log rollback failure but continue
            print(f"Rollback failed for step {step_name}: {str(e)}")
    
    async def execute_saga(
        self,
        saga_config: SagaConfiguration,
        input_data: Dict[str, Any]
    ) -> SagaExecution:
        """Execute a complete SAGA workflow"""
        # Parse YAML
        config = yaml.safe_load(saga_config.yaml_content)
        
        # Create execution record
        correlation_id = str(uuid.uuid4())
        execution = SagaExecution(
            saga_configuration_id=saga_config.id,
            correlation_id=correlation_id,
            status=SagaExecutionStatus.RUNNING,
            input_data=input_data
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        # Initialize context
        context = {
            "webhook": {
                "correlation_id": correlation_id,
                **input_data
            }
        }
        
        executed_steps: List[Dict[str, Any]] = []
        
        try:
            # Execute each step
            for step_config in config.get("executions", []):
                step_name = step_config["name"]
                step_type = step_config["type"]
                
                if step_type == "api":
                    step = await self._execute_api_step(step_config, context, execution, step_name)
                elif step_type == "kafka":
                    step = await self._execute_kafka_step(step_config, context, execution, step_name)
                else:
                    raise ValueError(f"Unknown step type: {step_type}")
                
                executed_steps.append({
                    "name": step_name,
                    "config": step_config,
                    "step": step
                })
                
                # Check if step failed
                if step.status == SagaExecutionStepStatus.FAILED:
                    # Rollback in reverse order
                    execution.status = SagaExecutionStatus.FAILED
                    execution.error_message = f"Step '{step_name}' failed: {step.error_message}"
                    
                    for executed in reversed(executed_steps):
                        await self._rollback_step(
                            executed["config"],
                            context,
                            executed["name"]
                        )
                        executed["step"].status = SagaExecutionStepStatus.ROLLED_BACK
                        self.db.commit()
                    
                    execution.status = SagaExecutionStatus.ROLLED_BACK
                    execution.completed_at = datetime.utcnow()
                    self.db.commit()
                    self.db.refresh(execution)
                    return execution
            
            # All steps completed successfully
            execution.status = SagaExecutionStatus.COMPLETED
            execution.output_data = context
            execution.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(execution)
            
            return execution
            
        except Exception as e:
            execution.status = SagaExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(execution)
            return execution
        
        finally:
            # Close Kafka producer
            if self.kafka_producer:
                self.kafka_producer.close()
                self.kafka_producer = None
