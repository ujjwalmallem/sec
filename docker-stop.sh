#!/bin/bash
# IBKR Whale Options Scanner - Docker Stop Script

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Stopping IBKR Whale Scanner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}docker-compose not found, trying 'docker compose'...${NC}"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Stop services
echo -e "${GREEN}Stopping all services...${NC}"
$DOCKER_COMPOSE down

# Check if user wants to remove volumes
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}Removing volumes (this will delete all database data)...${NC}"
    $DOCKER_COMPOSE down -v
    echo -e "${GREEN}Volumes removed.${NC}"
fi

echo -e "\n${GREEN}All services stopped.${NC}\n"

if [ "$1" != "--clean" ]; then
    echo -e "${YELLOW}To remove all data volumes, run: ./docker-stop.sh --clean${NC}\n"
fi
