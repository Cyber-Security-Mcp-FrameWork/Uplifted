#!/bin/bash
# Uplifted Health Check Script
# Verifies that the service is running and responding

set -e

# Configuration
MAIN_API_URL="${MAIN_API_URL:-http://localhost:7541}"
TOOLS_API_URL="${TOOLS_API_URL:-http://localhost:8086}"
TIMEOUT=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "curl not found, cannot perform health check"
    exit 1
fi

# Check Main API
check_main_api() {
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time "${TIMEOUT}" \
        "${MAIN_API_URL}/status" 2>/dev/null || echo "000")

    if [ "${status_code}" = "200" ]; then
        return 0
    else
        echo "Main API health check failed (status: ${status_code})"
        return 1
    fi
}

# Check Tools API
check_tools_api() {
    # Tools server may not have a /status endpoint, try root
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time "${TIMEOUT}" \
        "${TOOLS_API_URL}/" 2>/dev/null || echo "000")

    # Accept 200, 404, 405 as "server is running"
    if [ "${status_code}" = "200" ] || [ "${status_code}" = "404" ] || [ "${status_code}" = "405" ]; then
        return 0
    else
        echo "Tools API health check failed (status: ${status_code})"
        return 1
    fi
}

# Main health check
main() {
    local exit_code=0

    # Check Main API
    if check_main_api; then
        echo -e "${GREEN}✓${NC} Main API is healthy"
    else
        echo -e "${RED}✗${NC} Main API is unhealthy"
        exit_code=1
    fi

    # Check Tools API (optional, don't fail if it's not critical)
    if check_tools_api; then
        echo -e "${GREEN}✓${NC} Tools API is healthy"
    else
        echo -e "${RED}✗${NC} Tools API is unhealthy (warning)"
        # Don't fail on tools API check
    fi

    # Check Python process
    if pgrep -f "python.*server" > /dev/null; then
        echo -e "${GREEN}✓${NC} Server process is running"
    else
        echo -e "${RED}✗${NC} Server process not found"
        exit_code=1
    fi

    exit ${exit_code}
}

# Run health check
main
