#!/bin/bash

# Docker Helper Scripts for Django Subscription Project

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to setup environment
setup_env() {
    print_status "Setting up environment..."
    if [ ! -f .env ]; then
        cp env.docker .env
        print_warning "Created .env file from env.docker template. Please update with your actual values."
    else
        print_status ".env file already exists."
    fi
}

# Function to build and start services
start() {
    print_status "Starting Docker services..."
    check_docker
    setup_env
    
    # Build and start services
    docker-compose up --build -d
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    print_status "Running database migrations..."
    docker-compose exec web python manage.py migrate
    
    # Create superuser (optional)
    print_status "Creating superuser..."
    docker-compose exec web python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
    
    # Seed subscription plans
    print_status "Seeding subscription plans..."
    docker-compose exec web python manage.py seed_subscription_plans
    
    print_status "Services started successfully!"
    print_status "Web application: http://localhost:8000"
    print_status "Admin panel: http://localhost:8000/admin"
}

# Function to stop services
stop() {
    print_status "Stopping Docker services..."
    docker-compose down
    print_status "Services stopped."
}

# Function to restart services
restart() {
    print_status "Restarting Docker services..."
    stop
    start
}

# Function to view logs
logs() {
    if [ -z "$1" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$1"
    fi
}

# Function to run Django management commands
manage() {
    docker-compose exec web python manage.py "$@"
}

# Function to run shell
shell() {
    docker-compose exec web python manage.py shell
}

# Function to run tests
test() {
    docker-compose exec web python manage.py test
}

# Function to collect static files
collectstatic() {
    docker-compose exec web python manage.py collectstatic --noinput
}

# Function to show service status
status() {
    docker-compose ps
}

# Function to clean up
cleanup() {
    print_warning "This will remove all containers, volumes, and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up Docker resources..."
        docker-compose down -v --rmi all
        docker system prune -f
        print_status "Cleanup completed."
    else
        print_status "Cleanup cancelled."
    fi
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$2"
        ;;
    manage)
        shift
        manage "$@"
        ;;
    shell)
        shell
        ;;
    test)
        test
        ;;
    collectstatic)
        collectstatic
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|manage|shell|test|collectstatic|status|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start         - Build and start all services"
        echo "  stop          - Stop all services"
        echo "  restart       - Restart all services"
        echo "  logs [service] - View logs (optionally for specific service)"
        echo "  manage <cmd>  - Run Django management command"
        echo "  shell         - Open Django shell"
        echo "  test          - Run tests"
        echo "  collectstatic - Collect static files"
        echo "  status        - Show service status"
        echo "  cleanup       - Remove all containers and volumes"
        exit 1
        ;;
esac