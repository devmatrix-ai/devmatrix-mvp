# Troubleshooting Guide

Common issues and solutions for Devmatrix.

---

## 🚨 Common Issues

### 1. API Key Not Found

**Error**:
```
Error: ANTHROPIC_API_KEY environment variable not set
```

**Solution**:
1. Check if `.env` file exists in project root
2. Verify the file contains: `ANTHROPIC_API_KEY=your_key_here`
3. Reload environment: `source .env` or restart terminal
4. Verify with: `echo $ANTHROPIC_API_KEY`

**Alternative**: Set key directly in terminal
```bash
export ANTHROPIC_API_KEY="your_key_here"
```

---

### 2. Docker Services Not Running

**Error**:
```
Error: Could not connect to PostgreSQL/Redis
```

**Solution**:
```bash
# Check service status
dvmtx status

# Start services if stopped
dvmtx up

# Check Docker logs
docker-compose logs postgres
docker-compose logs redis

# Restart services
docker-compose down && docker-compose up -d
```

**Verify connection**:
```bash
# Test PostgreSQL
docker exec -it devmatrix-postgres psql -U devmatrix -d devmatrix -c "SELECT 1;"

# Test Redis
docker exec -it devmatrix-redis redis-cli ping
```

---

### 3. Import Errors / Module Not Found

**Error**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt

# Or install specific missing packages
pip install langchain langgraph langchain-anthropic

# Verify installation
pip list | grep langchain
```

**Note**: Ensure you're using Python 3.10 or higher
```bash
python --version  # Should be 3.10+
```

---

### 4. Permission Denied Errors

**Error**:
```
PermissionError: [Errno 13] Permission denied: '/workspace/...'
```

**Solution**:
```bash
# Fix workspace permissions
chmod -R 755 workspace/

# Or create workspace with correct permissions
mkdir -p workspace
chmod 755 workspace

# Check current permissions
ls -la workspace/
```

---

### 5. Git Repository Not Initialized

**Error**:
```
ValueError: Not a git repository: /path/to/workspace
```

**Solution**:
Devmatrix auto-initializes Git repos, but if you encounter this:

```bash
# Manual initialization
cd workspace/your-workspace-id
git init
git add .
git commit -m "Initial commit"

# Or let Devmatrix handle it
devmatrix generate "..." --workspace your-workspace-id  # Auto-init on first commit
```

---

### 6. Code Generation Hangs

**Symptom**: Code generation starts but never completes

**Possible Causes**:
1. **Anthropic API timeout**: Check internet connection
2. **Rate limiting**: Wait a few minutes and retry
3. **Large request**: Request might be too complex

**Solution**:
```bash
# Check API status
curl -I https://api.anthropic.com/v1/messages

# Simplify request
devmatrix generate "Create a simple hello world function"  # Start small

# Check logs
tail -f logs/devmatrix.log  # If logging is enabled
```

---

### 7. Test Failures

**Error**:
```
FAILED tests/test_something.py::test_name
```

**Solution**:
```bash
# Run specific test with verbose output
pytest tests/test_something.py::test_name -v

# Run with full error traceback
pytest tests/test_something.py -vvs

# Clear pytest cache
rm -rf .pytest_cache
pytest --cache-clear

# Reinstall dependencies
pip install -r requirements.txt
```

---

### 8. PostgreSQL Connection Failed

**Error**:
```
psycopg2.OperationalError: could not connect to server
```

**Solution**:
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check connection parameters in .env
cat .env | grep POSTGRES

# Verify port is not in use
lsof -i :5432  # Should show PostgreSQL or nothing

# Restart PostgreSQL
docker-compose restart postgres

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

---

### 9. Redis Connection Failed

**Error**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution**:
```bash
# Check Redis container
docker ps | grep redis

# Test connection
docker exec -it devmatrix-redis redis-cli ping
# Should return: PONG

# Check Redis logs
docker logs devmatrix-redis

# Restart Redis
docker-compose restart redis
```

---

### 10. Workspace Not Found

**Error**:
```
FileNotFoundError: Workspace 'my-workspace' does not exist
```

**Solution**:
```bash
# List all workspaces
devmatrix workspace list

# Create workspace
devmatrix workspace create my-workspace

# Or let generate create it automatically
devmatrix generate "..." --workspace my-workspace
```

---

## 🔍 Debugging Tips

### Enable Verbose Logging

```bash
# Set log level in environment
export LOG_LEVEL=DEBUG

# Run with verbose output
devmatrix generate "..." --verbose  # If implemented
```

### Check LangGraph Execution

```python
# Add this to your code for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# LangGraph will log each node execution
```

### Inspect Generated Code Before Approval

The agent shows you the code with syntax highlighting before asking for approval. Review:
- ✅ Type hints are present
- ✅ Docstrings are comprehensive
- ✅ Error handling is included
- ✅ Code follows PEP 8 style

### Test in Isolation

```bash
# Test workspace operations
python -c "from src.tools.workspace_manager import WorkspaceManager; ws = WorkspaceManager('test'); ws.create(); print('OK')"

# Test LLM connection
python -c "from src.llm.anthropic_client import AnthropicClient; client = AnthropicClient(); print(client.generate([{'role': 'user', 'content': 'Hello'}]))"

# Test database connections
python -c "from src.state.postgres_manager import PostgresManager; pg = PostgresManager(); print('PostgreSQL OK')"
python -c "from src.state.redis_manager import RedisManager; redis = RedisManager(); print('Redis OK')"
```

---

## 📊 Performance Issues

### Code Generation is Slow

**Expected**: 5-10 seconds per generation
**If slower**:
1. Check internet connection speed
2. Anthropic API might be experiencing delays
3. Complex requests take longer (expected)

**Optimization**:
```bash
# Use simpler prompts
devmatrix generate "Create add function"  # Fast

# Instead of
devmatrix generate "Create a comprehensive REST API client with authentication, retry logic, rate limiting, and error handling"  # Slow
```

### High Memory Usage

**If tests use too much memory**:
```bash
# Run tests in smaller batches
pytest tests/unit/
pytest tests/integration/

# Clear workspace after tests
rm -rf workspace/test-*
```

---

## 🐛 Bug Reports

If you encounter a bug not listed here:

1. **Check logs**: Look in `logs/` directory if logging is enabled
2. **Reproduce**: Try to reproduce with minimal example
3. **Gather info**:
   - Python version: `python --version`
   - Dependencies: `pip freeze`
   - OS: `uname -a` (Linux/Mac) or `systeminfo` (Windows)
   - Docker version: `docker --version`
4. **Create detailed issue**: Include error message, steps to reproduce, and environment info

---

## 💡 Best Practices

### Avoid Common Pitfalls

1. **Don't commit `.env` file**: It contains secrets
2. **Clean workspaces regularly**: Use `devmatrix workspace clean`
3. **Review code before approval**: Don't blindly approve everything
4. **Start simple**: Test with simple requests before complex ones
5. **Keep Docker running**: Services must be up for state management

### Optimal Workflow

```bash
# 1. Start services
dvmtx up && dvmtx status

# 2. Generate code
devmatrix generate "Clear, specific request"

# 3. Review and approve
# [Interactive approval in terminal]

# 4. Verify result
devmatrix files list my-workspace
devmatrix git status my-workspace

# 5. Clean up when done
devmatrix workspace clean --all
```

---

## 🆘 Getting Help

If issues persist:

1. **Check documentation**: `DOCS/` directory
2. **Review examples**: `examples/` directory
3. **Run diagnostics**: `devmatrix info`
4. **Check test suite**: `pytest -v` (all tests should pass)

---

**Last Updated**: 2025-10-11
