#!/bin/bash
# IBKR Whale Options Scanner - Docker Quick Start Script

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}IBKR Whale Options Scanner - Docker${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo -e "${YELLOW}Creating .env from .env.example...${NC}\n"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Please edit .env file with your configuration before continuing!${NC}"
    echo -e "${RED}At minimum, set:${NC}"
    echo -e "${RED}  - POSTGRES_PASSWORD (change from default)${NC}"
    echo -e "${RED}  - DATA_PROVIDER (ibkr or tradier)${NC}"
    echo -e "${RED}  - API credentials for your chosen data provider${NC}\n"
    read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
fi

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}docker-compose not found, trying 'docker compose'...${NC}"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p data logs

# Parse command line arguments
PROFILE=""
if [ "$1" == "--with-scanner" ]; then
    PROFILE="--profile scanner"
    echo -e "${GREEN}Starting with scanner service enabled...${NC}"
fi

# Stop any existing containers
echo -e "${GREEN}Stopping any existing containers...${NC}"
$DOCKER_COMPOSE down

# Build and start services
echo -e "${GREEN}Building Docker images...${NC}"
$DOCKER_COMPOSE build

echo -e "${GREEN}Starting services...${NC}"
$DOCKER_COMPOSE up -d $PROFILE

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 5

# Check service status
echo -e "\n${GREEN}Service Status:${NC}"
$DOCKER_COMPOSE ps

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Docker services are running!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "Access the applications at:"
echo -e "  ${BLUE}Main Web UI:${NC}      http://localhost:5000"
echo -e "  ${BLUE}Config UI:${NC}        http://localhost:5001"
echo -e "  ${BLUE}PostgreSQL:${NC}       localhost:5432\n"

echo -e "Useful commands:"
echo -e "  ${YELLOW}View logs:${NC}           $DOCKER_COMPOSE logs -f"
echo -e "  ${YELLOW}View web app logs:${NC}   $DOCKER_COMPOSE logs -f web-app"
echo -e "  ${YELLOW}Stop services:${NC}       $DOCKER_COMPOSE down"
echo -e "  ${YELLOW}Restart services:${NC}    $DOCKER_COMPOSE restart"
echo -e "  ${YELLOW}Run scanner:${NC}         $DOCKER_COMPOSE run --rm scanner\n"

echo -e "${GREEN}To start with scanner enabled: ./docker-start.sh --with-scanner${NC}\n"
