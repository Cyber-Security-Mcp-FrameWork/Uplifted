#!/bin/bash
# Uplifted Docker Entrypoint Script
# Handles initialization and service startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
print_banner() {
    cat << "EOF"
    _   _       _ _  __ _           _
   | | | |_ __ | (_)/ _| |_ ___  __| |
   | | | | '_ \| | | |_| __/ _ \/ _` |
   | |_| | |_) | | |  _| ||  __/ (_| |
    \___/| .__/|_|_|_|  \__\___|\__,_|
         |_|
EOF
    echo ""
    echo "Version: 0.53.1"
    echo "Environment: ${UPLIFTED_ENV:-development}"
    echo ""
}

# Initialize directories
init_directories() {
    log_info "Initializing directories..."

    # Create necessary directories
    mkdir -p "${UPLIFTED_DATA}" "${UPLIFTED_CONFIG}" "${UPLIFTED_LOGS}" "${UPLIFTED_PLUGINS}"

    # Set permissions
    chmod 755 "${UPLIFTED_DATA}" "${UPLIFTED_CONFIG}" "${UPLIFTED_LOGS}" "${UPLIFTED_PLUGINS}"

    log_success "Directories initialized"
}

# Generate default configuration
generate_config() {
    local config_file="${UPLIFTED_CONFIG}/config.yaml"

    if [ ! -f "${config_file}" ]; then
        log_info "Generating default configuration..."

        # Use Python to generate config
        python3 -c "
from uplifted.extensions import generate_config_template
import os

env = os.getenv('UPLIFTED_ENV', 'development')
template = 'production' if env == 'production' else 'development'

generate_config_template(
    template,
    '${config_file}',
    format='yaml'
)
print(f'Generated {template} configuration')
"
        log_success "Configuration generated: ${config_file}"
    else
        log_info "Configuration already exists: ${config_file}"
    fi
}

# Initialize plugins
init_plugins() {
    log_info "Initializing plugins..."

    # Check if plugins directory has example plugins
    if [ ! -d "${UPLIFTED_PLUGINS}/hello_world" ] && [ -d "/app/examples/plugins/hello_world" ]; then
        log_info "Copying example plugins..."
        cp -r /app/examples/plugins/* "${UPLIFTED_PLUGINS}/" 2>/dev/null || true
        log_success "Example plugins copied"
    fi

    log_success "Plugins initialized"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    # Check Python version
    python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: ${python_version}"

    # Check if required packages are installed
    if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
        log_error "Required packages not installed"
        exit 1
    fi

    log_success "Dependencies check passed"
}

# Run database migrations (if needed)
run_migrations() {
    log_info "Checking database..."

    if [ ! -f "${UPLIFTED_DATA}/uplifted.db" ]; then
        log_info "Database not found, will be created on first run"
    else
        log_info "Database found: ${UPLIFTED_DATA}/uplifted.db"
    fi
}

# Start server
start_server() {
    log_info "Starting Uplifted server..."
    log_info "Main API: http://0.0.0.0:7541"
    log_info "Tools Server: http://0.0.0.0:8086"
    log_info "API Documentation: http://0.0.0.0:7541/docs"
    echo ""

    # Set Python path
    export PYTHONPATH="/app:${PYTHONPATH}"

    # Run the server
    cd /app
    exec python3 -m server.run_main_server
}

# Main execution
main() {
    print_banner

    # Parse command
    COMMAND=${1:-server}

    case "${COMMAND}" in
        server)
            log_info "Starting in server mode..."
            init_directories
            generate_config
            init_plugins
            check_dependencies
            run_migrations
            start_server
            ;;

        bash|sh)
            log_info "Starting interactive shell..."
            exec /bin/bash
            ;;

        python)
            log_info "Starting Python interpreter..."
            shift
            exec python3 "$@"
            ;;

        test)
            log_info "Running tests..."
            exec python3 -m pytest tests/
            ;;

        config)
            log_info "Generating configuration..."
            init_directories
            generate_config
            log_success "Configuration generated in ${UPLIFTED_CONFIG}"
            ;;

        *)
            log_error "Unknown command: ${COMMAND}"
            echo ""
            echo "Available commands:"
            echo "  server  - Start Uplifted server (default)"
            echo "  bash    - Start interactive shell"
            echo "  python  - Start Python interpreter"
            echo "  test    - Run tests"
            echo "  config  - Generate configuration files"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
