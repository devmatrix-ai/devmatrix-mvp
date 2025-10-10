# Devmatrix CLI (dvmtx)

Command-line utility for managing Devmatrix services and development workflow.

## Installation

```bash
# From project root
./scripts/install-cli.sh

# System-wide (requires sudo)
./scripts/install-cli.sh --system
```

After installation, you can use `dvmtx` from anywhere.

---

## Quick Start

```bash
# Start services
dvmtx up

# Check status
dvmtx status

# View logs
dvmtx logs

# Stop services
dvmtx down
```

---

## Commands Reference

### Service Management

#### `dvmtx up`
Start all Devmatrix services (PostgreSQL + Redis)

```bash
dvmtx up
```

**Output:**
- Starts Docker containers
- Waits for health checks
- Shows service status

---

#### `dvmtx down`
Stop all services

```bash
dvmtx down
```

---

#### `dvmtx restart`
Restart all services

```bash
dvmtx restart
```

---

#### `dvmtx status`
Show service status and health checks

```bash
dvmtx status
```

**Shows:**
- Container status (Up/Down)
- PostgreSQL health
- Redis health

---

#### `dvmtx logs [service]`
View service logs (real-time)

```bash
# All services
dvmtx logs

# Specific service
dvmtx logs postgres
dvmtx logs redis
```

Press `Ctrl+C` to exit logs.

---

### Database Operations

#### `dvmtx db shell`
Open PostgreSQL interactive shell

```bash
dvmtx db shell
```

Inside the shell:
```sql
-- List tables
\dt devmatrix.*

-- Query projects
SELECT * FROM devmatrix.projects;

-- Exit
\q
```

---

#### `dvmtx db tables`
List all database tables

```bash
dvmtx db tables
```

---

#### `dvmtx db backup`
Create database backup

```bash
dvmtx db backup
```

Backup saved to: `backups/devmatrix-backup-YYYYMMDD-HHMMSS.sql`

---

### Redis Operations

#### `dvmtx redis cli`
Open Redis interactive CLI

```bash
dvmtx redis cli
```

Inside the CLI:
```redis
-- Ping
PING

-- Get all keys
KEYS *

-- Get value
GET key_name

-- Exit
EXIT
```

---

#### `dvmtx redis flush`
Flush all Redis data (DESTRUCTIVE!)

```bash
dvmtx redis flush
```

⚠️ **Warning:** This deletes ALL Redis data. Confirmation required.

---

### Development Tools

#### `dvmtx dev pgadmin`
Start pgAdmin database GUI

```bash
dvmtx dev pgadmin
```

Access at: http://localhost:5050

**Credentials:**
- Email: `admin@devmatrix.local`
- Password: `admin`

**Add Server:**
1. Right-click "Servers" → Register → Server
2. General tab:
   - Name: `Devmatrix Local`
3. Connection tab:
   - Host: `postgres` (or `localhost` if accessing from host)
   - Port: `5432`
   - Database: `devmatrix`
   - Username: `devmatrix`
   - Password: `devmatrix`

---

#### `dvmtx dev install`
Install Python dependencies

```bash
dvmtx dev install
```

Installs all packages from `requirements.txt`.

---

#### `dvmtx dev test`
Run test suite

```bash
dvmtx dev test
```

Runs pytest with coverage.

---

#### `dvmtx dev lint`
Run linters (ruff, black, mypy)

```bash
dvmtx dev lint
```

---

#### `dvmtx dev format`
Format code with Black

```bash
dvmtx dev format
```

---

### Cleanup

#### `dvmtx clean`
Delete all data (DESTRUCTIVE!)

```bash
dvmtx clean
```

⚠️ **Warning:** This deletes:
- All PostgreSQL data
- All Redis data
- All Docker volumes

Confirmation required.

---

## Environment Variables

Configure via `.env` file in project root:

```bash
# Database
POSTGRES_DB=devmatrix
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6379

# pgAdmin
PGADMIN_EMAIL=admin@devmatrix.local
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

---

## Troubleshooting

### Services won't start

**Check Docker:**
```bash
docker info
```

If Docker isn't running, start Docker Desktop.

---

### Port conflicts

**Check which process is using the port:**
```bash
# PostgreSQL (5432)
lsof -i :5432

# Redis (6379)
lsof -i :6379
```

**Kill the process:**
```bash
kill -9 <PID>
```

Or change ports in `.env` file.

---

### Database connection issues

**Test connection:**
```bash
dvmtx db shell
```

If fails, check:
1. Service is healthy: `dvmtx status`
2. Logs for errors: `dvmtx logs postgres`
3. Restart services: `dvmtx restart`

---

### Reset everything

**Nuclear option:**
```bash
# Stop services and delete all data
dvmtx clean

# Start fresh
dvmtx up
```

---

## Examples

### Daily Workflow

```bash
# Morning: Start services
dvmtx up

# Work...
dvmtx logs         # Check logs
dvmtx db shell     # Query database
dvmtx redis cli    # Check Redis

# End of day: Stop services
dvmtx down
```

---

### Development Workflow

```bash
# Start with pgAdmin
dvmtx dev pgadmin

# Install dependencies
dvmtx dev install

# Run tests
dvmtx dev test

# Format code
dvmtx dev format

# Check health
dvmtx status
```

---

### Debugging

```bash
# Check service health
dvmtx status

# View real-time logs
dvmtx logs postgres
dvmtx logs redis

# Open database shell
dvmtx db shell

# Check Redis
dvmtx redis cli
```

---

### Backup & Restore

```bash
# Create backup
dvmtx db backup

# Backups are in: backups/devmatrix-backup-*.sql

# Restore (manual):
docker exec -i devmatrix-postgres psql -U devmatrix devmatrix < backups/backup-file.sql
```

---

## Tips & Tricks

### Quick Status Check
```bash
alias dv='dvmtx'
dv status  # Shorter!
```

### Watch Logs
```bash
# Follow all logs with grep filter
dvmtx logs | grep ERROR
```

### Database Queries
```bash
# Run query without opening shell
docker exec devmatrix-postgres psql -U devmatrix -d devmatrix -c "SELECT count(*) FROM devmatrix.projects;"
```

### Redis Monitoring
```bash
# Monitor Redis commands in real-time
docker exec devmatrix-redis redis-cli MONITOR
```

---

## Script Maintenance

### Updating the CLI

```bash
# Pull latest changes
git pull

# Reinstall (updates symlink)
./scripts/install-cli.sh
```

### Uninstall

```bash
# Remove symlink
rm ~/.local/bin/dvmtx

# Or system-wide
sudo rm /usr/local/bin/dvmtx
```

---

## Version

Current version: **v0.1.0**

Last updated: 2025-10-10
