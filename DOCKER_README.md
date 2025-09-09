# Docker Setup for Django Subscription Project

This document provides instructions for running the Django subscription project using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Stripe account with API keys

## Quick Start

### 1. Environment Setup

Copy the environment template and update with your values:

```bash
cp env.docker .env
```

Edit `.env` file and update the following variables:
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key
- `STRIPE_SECRET_KEY`: Your Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook secret

### 2. Start Services

```bash
# Using the helper script
./docker-scripts.sh start

# Or using docker-compose directly
docker-compose up --build -d
```

### 3. Access the Application

- Web application: http://localhost:8000
- Admin panel: http://localhost:8000/admin
- Database: localhost:5432 (PostgreSQL)

## Available Services

The Docker setup includes the following services:

- **web**: Django application server
- **db**: PostgreSQL database
- **redis**: Redis for Celery task queue
- **celery**: Celery worker for background tasks
- **celery-beat**: Celery scheduler for periodic tasks

## Helper Scripts

The `docker-scripts.sh` script provides convenient commands:

```bash
# Start all services
./docker-scripts.sh start

# Stop all services
./docker-scripts.sh stop

# Restart all services
./docker-scripts.sh restart

# View logs
./docker-scripts.sh logs [service_name]

# Run Django management commands
./docker-scripts.sh manage migrate
./docker-scripts.sh manage createsuperuser
./docker-scripts.sh manage shell

# Run tests
./docker-scripts.sh test

# Collect static files
./docker-scripts.sh collectstatic

# Show service status
./docker-scripts.sh status

# Clean up (removes all containers and volumes)
./docker-scripts.sh cleanup
```

## Development vs Production

### Development

Use the default `docker-compose.yml` for development:

```bash
docker-compose up --build
```

Features:
- Hot reloading (code changes reflect immediately)
- Debug mode enabled
- SQLite fallback if PostgreSQL is not available
- Console email backend

### Production

Use `docker-compose.prod.yml` for production:

```bash
docker-compose -f docker-compose.prod.yml up --build -d
```

Features:
- Optimized multi-stage Docker build
- Gunicorn WSGI server
- Nginx reverse proxy
- PostgreSQL database
- Redis for caching and task queue
- Static file serving via Nginx
- Security headers
- Rate limiting
- SSL/HTTPS support (configure certificates)

## Database Management

### Migrations

```bash
# Run migrations
./docker-scripts.sh manage migrate

# Create new migration
./docker-scripts.sh manage makemigrations

# Show migration status
./docker-scripts.sh manage showmigrations
```

### Database Access

```bash
# Access PostgreSQL shell
docker-compose exec db psql -U postgres -d subscription_db

# Create database backup
docker-compose exec db pg_dump -U postgres subscription_db > backup.sql

# Restore database backup
docker-compose exec -T db psql -U postgres subscription_db < backup.sql
```

## Background Tasks

The project uses Celery for background tasks:

- **celery**: Worker process for executing tasks
- **celery-beat**: Scheduler for periodic tasks (trial expirations)

### Monitoring Celery

```bash
# View Celery logs
./docker-scripts.sh logs celery

# Monitor Celery tasks
docker-compose exec web python manage.py shell
>>> from celery import current_app
>>> current_app.control.inspect().active()
```

## Static Files

Static files are collected and served by Nginx in production:

```bash
# Collect static files
./docker-scripts.sh collectstatic

# Static files are served from /static/ URL
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

2. **Database connection issues**
   ```bash
   # Check database logs
   ./docker-scripts.sh logs db
   
   # Verify database is running
   ./docker-scripts.sh status
   ```

3. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

4. **Out of disk space**
   ```bash
   # Clean up Docker resources
   ./docker-scripts.sh cleanup
   docker system prune -a
   ```

### Logs

View logs for specific services:

```bash
# All services
./docker-scripts.sh logs

# Specific service
./docker-scripts.sh logs web
./docker-scripts.sh logs db
./docker-scripts.sh logs celery
```

### Debugging

Access the Django shell for debugging:

```bash
./docker-scripts.sh shell
```

## Environment Variables

Key environment variables:

- `DEBUG`: Enable/disable debug mode
- `SECRET_KEY`: Django secret key
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret

## Security Considerations

For production deployment:

1. Change default passwords and secrets
2. Use strong SECRET_KEY
3. Set DEBUG=False
4. Configure proper ALLOWED_HOSTS
5. Use HTTPS with SSL certificates
6. Regularly update Docker images
7. Use secrets management for sensitive data
8. Enable firewall rules
9. Monitor logs for suspicious activity

## Scaling

To scale the application:

```bash
# Scale web service
docker-compose up --scale web=3

# Scale celery workers
docker-compose up --scale celery=3
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec db pg_dump -U postgres subscription_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T db psql -U postgres subscription_db < backup_file.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v subscription_project_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v subscription_project_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
```

## Support

For issues and questions:
1. Check the logs: `./docker-scripts.sh logs`
2. Verify environment variables in `.env`
3. Ensure Docker is running properly
4. Check service status: `./docker-scripts.sh status`