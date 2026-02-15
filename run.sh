#!/bin/bash

################################################################################
# BTC Dashboard - Production Deployment Script
################################################################################
# Purpose:
#   1. Pull latest code from git repository
#   2. Install/update Python dependencies if needed
#   3. Restart the Streamlit web server using systemctl
#
# Safety Features:
#   - Fails fast on errors (set -euo pipefail)
#   - Idempotent - safe to run multiple times
#   - Clear logging with timestamps
#   - Validates environment before making changes
#
# Usage:
#   sudo ./run.sh
#
# Requirements:
#   - Ubuntu/Debian-like system
#   - Git repository initialized
#   - Python 3.x installed
#   - systemd service configured (btc-dashboard.service)
################################################################################

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

################################################################################
# Configuration
################################################################################

# Script directory (absolute path to repository root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Virtual environment directory
VENV_DIR="${SCRIPT_DIR}/.venv"

# Service name (adjust if your systemd service has a different name)
SERVICE_NAME="${SERVICE_NAME:-btc-dashboard.service}"

# Python executable (can be overridden by environment variable)
PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
PIP_BIN="${VENV_DIR}/bin/pip"

# Git branch to pull (can be overridden by environment variable)
GIT_BRANCH="${GIT_BRANCH:-main}"

# Dashboard port (must match btc-dashboard.service)
DASHBOARD_PORT="${DASHBOARD_PORT:-8502}"

# Log file
LOG_FILE="${SCRIPT_DIR}/deployment.log"

################################################################################
# Logging Functions
################################################################################

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] ERROR: $*" | tee -a "${LOG_FILE}" >&2
}

log_success() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] ✓ $*" | tee -a "${LOG_FILE}"
}

################################################################################
# Validation Functions
################################################################################

check_git_repo() {
    if [ ! -d .git ]; then
        log_error "Not a git repository. Please run this script from the repository root."
        exit 1
    fi
    log_success "Git repository validated"
}

check_python() {
    if [ ! -d "${VENV_DIR}" ]; then
        log_error "Virtual environment not found at ${VENV_DIR}"
        log_error "Please run install-service.sh first to create the virtual environment"
        exit 1
    fi

    if ! command -v "${PYTHON_BIN}" &> /dev/null; then
        log_error "Python not found: ${PYTHON_BIN}"
        log_error "Please run install-service.sh first to set up the environment"
        exit 1
    fi
    local python_version
    python_version=$("${PYTHON_BIN}" --version 2>&1)
    log_success "Python found: ${python_version}"
}

check_requirements_file() {
    if [ ! -f requirements.txt ]; then
        log_error "requirements.txt not found"
        exit 1
    fi
    log_success "requirements.txt found"
}

check_systemd_service() {
    if ! systemctl list-unit-files "${SERVICE_NAME}" &> /dev/null; then
        log_error "Systemd service '${SERVICE_NAME}' not found"
        log_error "Please create the service file first or set SERVICE_NAME environment variable"
        exit 1
    fi
    log_success "Systemd service '${SERVICE_NAME}' found"
}

################################################################################
# Main Deployment Functions
################################################################################

git_pull() {
    log "Pulling latest code from git..."

    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        log "Local changes detected, stashing..."
        git stash save "Auto-stash before deployment $(date '+%Y-%m-%d %H:%M:%S')" || true
    fi

    # Fetch latest changes
    log "Fetching from remote..."
    git fetch origin

    # Check current branch
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    log "Current branch: ${current_branch}"

    # Pull latest changes
    log "Pulling changes for branch: ${GIT_BRANCH}"
    git pull origin "${GIT_BRANCH}"

    log_success "Git pull completed"
}

install_dependencies() {
    log "Checking Python dependencies..."

    # Create requirements checksum file if it doesn't exist
    local req_checksum_file="${SCRIPT_DIR}/.requirements.checksum"
    local current_checksum
    current_checksum=$(md5sum requirements.txt | awk '{print $1}')

    # Check if requirements have changed
    if [ -f "${req_checksum_file}" ]; then
        local previous_checksum
        previous_checksum=$(cat "${req_checksum_file}")

        if [ "${current_checksum}" = "${previous_checksum}" ]; then
            log "Requirements unchanged, skipping dependency installation"
            return 0
        else
            log "Requirements changed, updating dependencies..."
        fi
    else
        log "First run or checksum missing, installing dependencies..."
    fi

    # Install/update dependencies in virtual environment
    log "Installing Python dependencies..."
    "${PIP_BIN}" install --upgrade pip
    "${PIP_BIN}" install -r requirements.txt

    # Save new checksum
    echo "${current_checksum}" > "${req_checksum_file}"

    log_success "Dependencies installed/updated"
}

restart_service() {
    log "Restarting systemd service: ${SERVICE_NAME}"

    # Clear any start-limit failures from previous runs
    sudo systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

    # Check if service is active
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "Service is currently active, restarting..."
        sudo systemctl restart "${SERVICE_NAME}"
    else
        log "Service is not active, starting..."
        sudo systemctl start "${SERVICE_NAME}"
    fi

    # Wait for Streamlit to fully initialize (increased from 2 to 15 seconds)
    log "Waiting for service to initialize..."
    sleep 15

    # Verify service is running
    if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_error "Service '${SERVICE_NAME}' failed to start"
        log "Checking service status..."
        sudo systemctl status "${SERVICE_NAME}" --no-pager || true
        exit 1
    fi

    # Check for recent errors in journal
    log "Checking for errors in service logs..."
    local error_count
    error_count=$(sudo journalctl -u "${SERVICE_NAME}" --since "30 seconds ago" --no-pager | grep -ciE "(error|failed|exception|traceback)" || true)

    if [ "${error_count}" -gt 0 ]; then
        log_error "Found ${error_count} error(s) in service logs within the last 30 seconds"
        log "Recent service logs:"
        sudo journalctl -u "${SERVICE_NAME}" --since "30 seconds ago" --no-pager -n 50 || true
        exit 1
    fi

    # Verify service is actually responding on port ${DASHBOARD_PORT}
    log "Verifying service is responding on port ${DASHBOARD_PORT}..."
    if command -v curl &> /dev/null; then
        if curl -sf --max-time 5 http://127.0.0.1:${DASHBOARD_PORT} > /dev/null 2>&1; then
            log_success "Service '${SERVICE_NAME}' is running and responding on port ${DASHBOARD_PORT}"
        else
            log_error "Service is active but not responding on port ${DASHBOARD_PORT}"
            log "This may indicate a port conflict or application startup failure"
            log "Recent service logs:"
            sudo journalctl -u "${SERVICE_NAME}" --since "30 seconds ago" --no-pager -n 50 || true
            exit 1
        fi
    else
        log "curl not available, skipping port check"
        log_success "Service '${SERVICE_NAME}' is running"
    fi
}

show_service_status() {
    log "Current service status:"
    sudo systemctl status "${SERVICE_NAME}" --no-pager || true
}

################################################################################
# Main Execution
################################################################################

main() {
    log "=========================================="
    log "BTC Dashboard Deployment Script"
    log "=========================================="
    log "Script directory: ${SCRIPT_DIR}"
    log "Service name: ${SERVICE_NAME}"
    log "Python binary: ${PYTHON_BIN}"
    log "Git branch: ${GIT_BRANCH}"
    log "=========================================="

    # Pre-deployment validation
    log "Running pre-deployment checks..."
    check_git_repo
    check_python
    check_requirements_file
    check_systemd_service
    log_success "All pre-deployment checks passed"

    # Deployment steps
    log ""
    log "Starting deployment..."

    # Step 1: Pull latest code
    git_pull

    # Step 2: Install/update dependencies
    install_dependencies

    # Step 3: Restart service
    restart_service

    # Show final status
    log ""
    show_service_status

    log ""
    log_success "=========================================="
    log_success "Deployment completed successfully!"
    log_success "=========================================="
}

# Run main function
main "$@"
