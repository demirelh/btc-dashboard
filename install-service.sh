#!/bin/bash

################################################################################
# BTC Dashboard - Systemd Service Installation Script
################################################################################
# Purpose:
#   Installs and configures the btc-dashboard systemd service
#
# Usage:
#   sudo ./install-service.sh
#
# Requirements:
#   - Run with sudo or as root
#   - systemd-based Linux system
#   - Python 3.x installed
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="${SCRIPT_DIR}/btc-dashboard.service"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_NAME="btc-dashboard.service"

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        log_info "Usage: sudo ./install-service.sh"
        exit 1
    fi
    log_success "Running as root"
}

check_systemd() {
    if ! command -v systemctl &> /dev/null; then
        log_error "systemctl not found. This script requires a systemd-based Linux system."
        exit 1
    fi
    log_success "systemd detected"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found. Please install Python 3.x first."
        exit 1
    fi
    local python_version
    python_version=$(python3 --version 2>&1)
    log_success "Python found: ${python_version}"
}

check_service_file() {
    if [ ! -f "${SERVICE_FILE}" ]; then
        log_error "Service file not found: ${SERVICE_FILE}"
        log_error "Make sure you're running this script from the btc-dashboard directory"
        exit 1
    fi
    log_success "Service file found: ${SERVICE_FILE}"
}

################################################################################
# Installation Functions
################################################################################

backup_existing_service() {
    local installed_service="${SYSTEMD_DIR}/${SERVICE_NAME}"

    if [ -f "${installed_service}" ]; then
        log_warn "Existing service file found"

        # Create backup
        local backup_file="${installed_service}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "${installed_service}" "${backup_file}"
        log_info "Backed up to: ${backup_file}"

        # Stop service if running
        if systemctl is-active --quiet "${SERVICE_NAME}"; then
            log_info "Stopping running service..."
            systemctl stop "${SERVICE_NAME}"
            log_success "Service stopped"
        fi
    fi
}

install_service() {
    log_info "Installing service file..."

    # Copy service file to systemd directory
    cp "${SERVICE_FILE}" "${SYSTEMD_DIR}/"
    chmod 644 "${SYSTEMD_DIR}/${SERVICE_NAME}"

    log_success "Service file installed to ${SYSTEMD_DIR}/${SERVICE_NAME}"
}

reload_systemd() {
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload
    log_success "Systemd daemon reloaded"
}

enable_service() {
    log_info "Enabling service to start on boot..."
    systemctl enable "${SERVICE_NAME}"
    log_success "Service enabled"
}

start_service() {
    log_info "Starting service..."
    systemctl start "${SERVICE_NAME}"

    # Wait a moment for service to start
    sleep 2

    # Check if service started successfully
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_success "Service started successfully"
    else
        log_error "Service failed to start"
        log_error "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
        exit 1
    fi
}

show_status() {
    log_info "Service status:"
    echo ""
    systemctl status "${SERVICE_NAME}" --no-pager || true
}

show_summary() {
    echo ""
    echo "========================================"
    log_success "Installation Complete!"
    echo "========================================"
    echo ""
    echo "Service: ${SERVICE_NAME}"
    echo "Status: $(systemctl is-active ${SERVICE_NAME})"
    echo "Enabled on boot: $(systemctl is-enabled ${SERVICE_NAME})"
    echo ""
    echo "Useful commands:"
    echo "  - View status:  sudo systemctl status ${SERVICE_NAME}"
    echo "  - View logs:    sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  - Restart:      sudo systemctl restart ${SERVICE_NAME}"
    echo "  - Stop:         sudo systemctl stop ${SERVICE_NAME}"
    echo "  - Disable:      sudo systemctl disable ${SERVICE_NAME}"
    echo ""
    echo "Web interface: http://127.0.0.1:8501"
    echo "HTTPS access: See REVERSE_PROXY_SETUP.md"
    echo ""
    echo "For deployment: sudo ./run.sh"
    echo ""
    echo "Documentation:"
    echo "  - SERVICE_INSTALLATION.md"
    echo "  - REVERSE_PROXY_SETUP.md"
    echo "========================================"
}

################################################################################
# Main Installation Process
################################################################################

main() {
    echo "========================================"
    echo "BTC Dashboard Service Installer"
    echo "========================================"
    echo ""

    # Pre-installation checks
    log_info "Running pre-installation checks..."
    check_root
    check_systemd
    check_python
    check_service_file
    echo ""

    # Installation steps
    log_info "Starting installation..."
    echo ""

    backup_existing_service
    install_service
    reload_systemd
    enable_service
    start_service

    echo ""
    show_status
    echo ""
    show_summary
}

# Run main installation
main "$@"
