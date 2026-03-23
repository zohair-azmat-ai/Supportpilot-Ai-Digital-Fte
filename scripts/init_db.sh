#!/usr/bin/env bash
# =============================================================================
# SupportPilot AI — Database Initialization Script
# =============================================================================
#
# This script automates the database setup process:
#   1. Creates a Python virtual environment (if it doesn't exist)
#   2. Installs all backend dependencies from requirements.txt
#   3. Runs Alembic migrations to bring the schema to the latest revision
#   4. Optionally seeds the database with sample data
#
# Usage:
#   ./scripts/init_db.sh [OPTIONS]
#
# Options:
#   --seed        Run the seed script after migrations
#   --help        Show this help message
#
# Examples:
#   ./scripts/init_db.sh                   # Migrate only
#   ./scripts/init_db.sh --seed            # Migrate + seed sample data
#
# Prerequisites:
#   - Python 3.11+ installed and available as `python3` or `python`
#   - DATABASE_URL configured in backend/.env
#   - Run from the project root directory
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors and formatting
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}============================================================${RESET}"
    echo -e "${BOLD}${BLUE}  SupportPilot AI — Database Initialization${RESET}"
    echo -e "${BOLD}${BLUE}============================================================${RESET}"
    echo ""
}

print_step() {
    echo -e "${CYAN}${BOLD}──> $1${RESET}"
}

print_success() {
    echo -e "  ${GREEN}✓ $1${RESET}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠ $1${RESET}"
}

print_error() {
    echo -e "  ${RED}✗ $1${RESET}"
}

print_info() {
    echo -e "  ${BLUE}ℹ $1${RESET}"
}

show_help() {
    echo ""
    echo -e "${BOLD}SupportPilot AI — Database Initialization Script${RESET}"
    echo ""
    echo -e "${BOLD}USAGE:${RESET}"
    echo "  ./scripts/init_db.sh [OPTIONS]"
    echo ""
    echo -e "${BOLD}OPTIONS:${RESET}"
    echo "  --seed      Run seed script after migrations (creates sample data)"
    echo "  --help      Show this help message"
    echo ""
    echo -e "${BOLD}EXAMPLES:${RESET}"
    echo "  ./scripts/init_db.sh              # Run migrations only"
    echo "  ./scripts/init_db.sh --seed       # Migrate + seed sample data"
    echo ""
    echo -e "${BOLD}PREREQUISITES:${RESET}"
    echo "  - Python 3.11+ must be installed"
    echo "  - backend/.env must exist with DATABASE_URL configured"
    echo "  - Run from the project root directory"
    echo ""
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
RUN_SEED=false

for arg in "$@"; do
    case "$arg" in
        --seed)
            RUN_SEED=true
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_error "Unknown option: $arg"
            echo "  Run './scripts/init_db.sh --help' for usage."
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Determine project root (script is in scripts/, so parent is project root)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"
REQUIREMENTS="$BACKEND_DIR/requirements.txt"
ENV_FILE="$BACKEND_DIR/.env"
SEED_SCRIPT="$SCRIPT_DIR/seed.py"

print_header

echo -e "  ${BOLD}Project root:${RESET} $PROJECT_ROOT"
echo -e "  ${BOLD}Backend path:${RESET} $BACKEND_DIR"
echo -e "  ${BOLD}Seed data:${RESET}    $([ "$RUN_SEED" = true ] && echo 'Yes' || echo 'No')"
echo ""

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
print_step "Checking prerequisites"

# Check we're in the right place
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    print_info "Make sure you're running this script from the project root."
    exit 1
fi

if [ ! -f "$REQUIREMENTS" ]; then
    print_error "requirements.txt not found at: $REQUIREMENTS"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found at: $ENV_FILE"
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        print_info "Copying .env.example to .env..."
        cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
        print_warning "Please edit $ENV_FILE with your configuration before proceeding."
        echo ""
        echo -e "  ${YELLOW}Required variables:${RESET}"
        echo "    DATABASE_URL    — PostgreSQL connection string"
        echo "    SECRET_KEY      — JWT signing key"
        echo "    OPENAI_API_KEY  — OpenAI API key"
        echo ""
        read -p "  Continue with current .env values? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Edit $ENV_FILE and re-run this script."
            exit 0
        fi
    else
        print_error "No .env or .env.example found. Cannot proceed."
        exit 1
    fi
fi

# Find Python
PYTHON=""
for cmd in python3.11 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | awk '{print $2}')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    print_error "Python 3.11+ not found. Please install it and try again."
    print_info "Download: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" --version 2>&1)
print_success "Found $PYTHON_VERSION"

# ---------------------------------------------------------------------------
# Step 1: Create virtual environment
# ---------------------------------------------------------------------------
print_step "Setting up virtual environment"

if [ -d "$VENV_DIR" ]; then
    print_success "Virtual environment already exists: $VENV_DIR"
else
    print_info "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    print_success "Virtual environment created: $VENV_DIR"
fi

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    VENV_ACTIVATE="$VENV_DIR/Scripts/activate"
else
    VENV_ACTIVATE="$VENV_DIR/bin/activate"
fi

if [ ! -f "$VENV_ACTIVATE" ]; then
    print_error "Could not find activation script: $VENV_ACTIVATE"
    exit 1
fi

# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
print_success "Virtual environment activated"

# ---------------------------------------------------------------------------
# Step 2: Install dependencies
# ---------------------------------------------------------------------------
print_step "Installing Python dependencies"

pip install --upgrade pip --quiet
print_success "pip upgraded"

pip install -r "$REQUIREMENTS" --quiet
print_success "All dependencies installed from requirements.txt"

# ---------------------------------------------------------------------------
# Step 3: Run Alembic migrations
# ---------------------------------------------------------------------------
print_step "Running database migrations"

cd "$BACKEND_DIR"

# Check if alembic is accessible
if ! command -v alembic &>/dev/null; then
    print_error "alembic not found in PATH after installing requirements."
    print_info "Try activating the venv manually: source $VENV_ACTIVATE"
    exit 1
fi

# Show current migration state
echo ""
print_info "Current migration state:"
alembic current 2>&1 | sed 's/^/    /' || true
echo ""

print_info "Applying migrations..."
alembic upgrade head

print_success "Migrations applied successfully"

# Show updated state
echo ""
print_info "Migration state after upgrade:"
alembic current 2>&1 | sed 's/^/    /' || true
echo ""

# ---------------------------------------------------------------------------
# Step 4: Seed database (optional)
# ---------------------------------------------------------------------------
if [ "$RUN_SEED" = true ]; then
    print_step "Seeding database with sample data"

    if [ ! -f "$SEED_SCRIPT" ]; then
        print_error "Seed script not found: $SEED_SCRIPT"
        exit 1
    fi

    cd "$PROJECT_ROOT"
    python "$SEED_SCRIPT"
else
    print_info "Skipping seed. Run with --seed to create sample data."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}============================================================${RESET}"
echo -e "${BOLD}${GREEN}  Database initialization complete!${RESET}"
echo -e "${BOLD}${GREEN}============================================================${RESET}"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "    1. Start the backend:  ${CYAN}uvicorn app.main:app --reload${RESET}"
echo -e "       (from the ${CYAN}backend/${RESET} directory with venv activated)"
echo -e "    2. Start the frontend: ${CYAN}npm run dev${RESET}"
echo -e "       (from the ${CYAN}frontend/${RESET} directory)"
echo ""
if [ "$RUN_SEED" = true ]; then
    echo -e "  ${BOLD}Admin login:${RESET}"
    echo -e "    Email:    ${CYAN}admin@supportpilot.ai${RESET}"
    echo -e "    Password: ${CYAN}Admin123!${RESET}"
    echo ""
fi
