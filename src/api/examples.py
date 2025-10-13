"""
API Usage Examples

Example requests and responses for the Devmatrix API.
"""

# Example 1: Create a simple workflow
CREATE_WORKFLOW_EXAMPLE = {
    "name": "Data Processing Pipeline",
    "description": "Process and analyze data files",
    "tasks": [
        {
            "task_id": "fetch_data",
            "agent_type": "data_fetcher",
            "prompt": "Fetch data from source",
            "dependencies": [],
            "max_retries": 3,
            "timeout": 300
        },
        {
            "task_id": "validate_data",
            "agent_type": "data_validator",
            "prompt": "Validate data quality",
            "dependencies": ["fetch_data"],
            "max_retries": 2,
            "timeout": 180
        },
        {
            "task_id": "process_data",
            "agent_type": "data_processor",
            "prompt": "Process and transform data",
            "dependencies": ["validate_data"],
            "max_retries": 3,
            "timeout": 600
        },
        {
            "task_id": "generate_report",
            "agent_type": "report_generator",
            "prompt": "Generate analysis report",
            "dependencies": ["process_data"],
            "max_retries": 2,
            "timeout": 300
        }
    ],
    "metadata": {
        "owner": "data_team",
        "environment": "production"
    }
}


# Example 2: Create a code analysis workflow
CODE_ANALYSIS_WORKFLOW = {
    "name": "Code Quality Analysis",
    "description": "Analyze code quality and generate improvement recommendations",
    "tasks": [
        {
            "task_id": "scan_codebase",
            "agent_type": "code_scanner",
            "prompt": "Scan codebase for issues",
            "dependencies": [],
            "max_retries": 2,
            "timeout": 300
        },
        {
            "task_id": "analyze_patterns",
            "agent_type": "pattern_analyzer",
            "prompt": "Analyze code patterns and anti-patterns",
            "dependencies": ["scan_codebase"],
            "max_retries": 2,
            "timeout": 400
        },
        {
            "task_id": "security_audit",
            "agent_type": "security_auditor",
            "prompt": "Perform security audit",
            "dependencies": ["scan_codebase"],
            "max_retries": 3,
            "timeout": 500
        },
        {
            "task_id": "generate_recommendations",
            "agent_type": "recommendation_engine",
            "prompt": "Generate improvement recommendations",
            "dependencies": ["analyze_patterns", "security_audit"],
            "max_retries": 2,
            "timeout": 300
        }
    ],
    "metadata": {
        "owner": "engineering_team",
        "priority": "high"
    }
}


# Example 3: Start an execution
START_EXECUTION_EXAMPLE = {
    "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "input_data": {
        "source_path": "/data/input",
        "output_path": "/data/output",
        "config": {
            "batch_size": 100,
            "parallel_workers": 4
        }
    },
    "priority": 8
}


# Example 4: Workflow response
WORKFLOW_RESPONSE_EXAMPLE = {
    "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Data Processing Pipeline",
    "description": "Process and analyze data files",
    "tasks": [
        {
            "task_id": "fetch_data",
            "agent_type": "data_fetcher",
            "prompt": "Fetch data from source",
            "dependencies": [],
            "max_retries": 3,
            "timeout": 300
        }
    ],
    "metadata": {
        "owner": "data_team",
        "environment": "production"
    },
    "created_at": "2024-10-13T12:00:00Z",
    "updated_at": "2024-10-13T12:00:00Z"
}


# Example 5: Execution response
EXECUTION_RESPONSE_EXAMPLE = {
    "execution_id": "x9y8z7w6-v5u4-3210-zyxw-v9876543210",
    "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "running",
    "input_data": {
        "source_path": "/data/input",
        "output_path": "/data/output"
    },
    "priority": 8,
    "task_statuses": [
        {
            "task_id": "fetch_data",
            "status": "completed",
            "started_at": "2024-10-13T12:05:00Z",
            "completed_at": "2024-10-13T12:05:30Z",
            "error": None,
            "result": {"records_fetched": 1000}
        },
        {
            "task_id": "validate_data",
            "status": "running",
            "started_at": "2024-10-13T12:05:30Z",
            "completed_at": None,
            "error": None,
            "result": None
        }
    ],
    "started_at": "2024-10-13T12:05:00Z",
    "completed_at": None,
    "error": None,
    "result": None,
    "created_at": "2024-10-13T12:04:00Z"
}


# Example 6: Metrics summary
METRICS_SUMMARY_EXAMPLE = {
    "total_workflows": 15,
    "total_executions": 47,
    "executions_by_status": {
        "completed": 32,
        "running": 3,
        "failed": 8,
        "pending": 2,
        "cancelled": 2
    },
    "avg_execution_time_seconds": 245.6
}


# Example 7: Health check response
HEALTH_CHECK_EXAMPLE = {
    "status": "healthy",
    "timestamp": "2024-10-13T12:00:00.000Z",
    "components": {
        "system": {
            "name": "system",
            "status": "healthy",
            "message": "System operational",
            "latency_ms": 0.5,
            "metadata": {},
            "last_check": "2024-10-13T12:00:00.000Z"
        }
    }
}


# cURL examples for testing
CURL_EXAMPLES = """
# Create a workflow
curl -X POST "http://localhost:8000/api/v1/workflows" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Test Workflow",
    "description": "A test workflow",
    "tasks": [
      {
        "task_id": "task1",
        "agent_type": "test_agent",
        "prompt": "Do something",
        "dependencies": [],
        "max_retries": 3,
        "timeout": 300
      }
    ]
  }'

# List all workflows
curl -X GET "http://localhost:8000/api/v1/workflows"

# Get workflow by ID
curl -X GET "http://localhost:8000/api/v1/workflows/{workflow_id}"

# Update workflow
curl -X PUT "http://localhost:8000/api/v1/workflows/{workflow_id}" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Updated Workflow Name"}'

# Delete workflow
curl -X DELETE "http://localhost:8000/api/v1/workflows/{workflow_id}"

# Start execution
curl -X POST "http://localhost:8000/api/v1/executions" \\
  -H "Content-Type: application/json" \\
  -d '{
    "workflow_id": "{workflow_id}",
    "input_data": {"key": "value"},
    "priority": 5
  }'

# List executions
curl -X GET "http://localhost:8000/api/v1/executions"

# Get execution status
curl -X GET "http://localhost:8000/api/v1/executions/{execution_id}"

# Cancel execution
curl -X POST "http://localhost:8000/api/v1/executions/{execution_id}/cancel"

# Get metrics
curl -X GET "http://localhost:8000/api/v1/metrics"

# Get metrics summary
curl -X GET "http://localhost:8000/api/v1/metrics/summary"

# Health check
curl -X GET "http://localhost:8000/api/v1/health"

# Liveness probe
curl -X GET "http://localhost:8000/api/v1/health/live"

# Readiness probe
curl -X GET "http://localhost:8000/api/v1/health/ready"

# OpenAPI docs (browser)
open http://localhost:8000/docs

# ReDoc documentation (browser)
open http://localhost:8000/redoc
"""
