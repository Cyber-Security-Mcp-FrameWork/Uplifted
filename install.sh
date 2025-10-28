#!/bin/bash
# Uplifted One-Click Installation Script for Linux/macOS
# Automatically installs and configures Uplifted

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${UPLIFTED_INSTALL_DIR:-$HOME/.uplifted}"
PYTHON_MIN_VERSION="3.10"
REPO_URL="https://github.com/uplifted/uplifted.git"
BRANCH="${UPLIFTED_BRANCH:-main}"

# Functions
print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
    _   _       _ _  __ _           _
   | | | |_ __ | (_)/ _| |_ ___  __| |
   | | | | '_ \| | | |_| __/ _ \/ _` |
   | |_| | |_) | | |  _| ||  __/ (_| |
    \___/| .__/|_|_|_|  \__\___|\__,_|
         |_|

    One-Click Installation Script
EOF
    echo -e "${NC}"
}

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

log_step() {
    echo -e "${PURPLE}[STEP $1]${NC} $2"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    else
        log_error "Unsupported OS: $OSTYPE"
        exit 1
    fi

    log_info "Detected OS: $OS ($DISTRO)"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root. This is not recommended."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Check Python version
check_python() {
    log_step 1 "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python $PYTHON_MIN_VERSION or higher."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Found Python $PYTHON_VERSION"

    # Version comparison
    if [ "$(printf '%s\n' "$PYTHON_MIN_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$PYTHON_MIN_VERSION" ]; then
        log_error "Python $PYTHON_MIN_VERSION or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi

    log_success "Python version check passed"
}

# Install system dependencies
install_system_deps() {
    log_step 2 "Installing system dependencies..."

    case $DISTRO in
        ubuntu|debian)
            log_info "Installing dependencies for Ubuntu/Debian..."
            sudo apt-get update
            sudo apt-get install -y \
                git curl wget \
                build-essential \
                python3-pip python3-venv \
                libx11-6 libxtst6 libxrandr2 libxi6 \
                libfreetype6 libpng16-16 \
                libglib2.0-0 libsm6 libxext6 libxrender1
            ;;

        centos|rhel|fedora)
            log_info "Installing dependencies for CentOS/RHEL/Fedora..."
            sudo yum install -y \
                git curl wget \
                gcc gcc-c++ make \
                python3-pip python3-devel \
                libX11 libXtst libXrandr libXi \
                freetype libpng \
                glib2 libSM libXext libXrender
            ;;

        arch|manjaro)
            log_info "Installing dependencies for Arch/Manjaro..."
            sudo pacman -Syu --noconfirm \
                git curl wget \
                base-devel \
                python python-pip \
                libx11 libxtst libxrandr libxi \
                freetype2 libpng \
                glib2 libsm libxext libxrender
            ;;

        macos)
            log_info "Installing dependencies for macOS..."
            if ! command -v brew &> /dev/null; then
                log_warning "Homebrew not found. Installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install git python@3.11
            ;;

        *)
            log_warning "Unknown distribution. Skipping system dependency installation."
            log_info "Please install git, curl, python3, and build tools manually."
            ;;
    esac

    log_success "System dependencies installed"
}

# Clone or update repository
setup_repository() {
    log_step 3 "Setting up repository..."

    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Installation directory already exists: $INSTALL_DIR"
        read -p "Update existing installation? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Skipping repository setup"
            return
        fi

        log_info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull origin $BRANCH
    else
        log_info "Cloning repository to $INSTALL_DIR..."
        git clone --branch $BRANCH $REPO_URL "$INSTALL_DIR"
    fi

    cd "$INSTALL_DIR"
    log_success "Repository setup complete"
}

# Create virtual environment and install dependencies
setup_python_env() {
    log_step 4 "Setting up Python environment..."

    cd "$INSTALL_DIR"

    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    else
        log_info "Virtual environment already exists"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip

    # Install uv for faster dependency installation
    log_info "Installing uv..."
    pip install uv

    # Install dependencies
    log_info "Installing dependencies (this may take a few minutes)..."
    uv pip install -e .

    log_success "Python environment setup complete"
}

# Generate configuration
generate_config() {
    log_step 5 "Generating configuration..."

    cd "$INSTALL_DIR"
    source venv/bin/activate

    # Create config directory
    mkdir -p config data logs plugins

    # Generate default configuration
    if [ ! -f "config/config.yaml" ]; then
        log_info "Generating default configuration..."
        python3 -c "
from uplifted.extensions import generate_config_template
generate_config_template('development', 'config/config.yaml')
print('Configuration generated: config/config.yaml')
"
    else
        log_info "Configuration already exists: config/config.yaml"
    fi

    # Copy environment template
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        cp .env.example .env
        log_warning "Please edit .env and add your API keys"
    fi

    log_success "Configuration generated"
}

# Create systemd service (optional)
create_systemd_service() {
    if [ "$OS" != "linux" ]; then
        return
    fi

    log_step 6 "Setting up systemd service (optional)..."

    read -p "Install as systemd service? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Skipping systemd service setup"
        return
    fi

    log_info "Creating systemd service..."

    SERVICE_FILE="/etc/systemd/system/uplifted.service"

    sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Uplifted AI Agent System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m server.run_main_server
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable uplifted

    log_success "Systemd service created"
    log_info "Start with: sudo systemctl start uplifted"
    log_info "View logs with: sudo journalctl -u uplifted -f"
}

# Create launcher scripts
create_launchers() {
    log_step 7 "Creating launcher scripts..."

    cd "$INSTALL_DIR"

    # Create start script
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -m server.run_main_server
EOF
    chmod +x start.sh

    # Create stop script
    cat > stop.sh << 'EOF'
#!/bin/bash
pkill -f "python.*server.run_main_server"
EOF
    chmod +x stop.sh

    # Create status script
    cat > status.sh << 'EOF'
#!/bin/bash
if pgrep -f "python.*server.run_main_server" > /dev/null; then
    echo "✓ Uplifted is running"
    pgrep -f "python.*server.run_main_server" | xargs ps -p
else
    echo "✗ Uplifted is not running"
fi
EOF
    chmod +x status.sh

    log_success "Launcher scripts created"
}

# Add to PATH (optional)
add_to_path() {
    log_step 8 "Adding to PATH (optional)..."

    read -p "Add uplifted to PATH? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Skipping PATH setup"
        return
    fi

    # Determine shell config file
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    # Add alias
    ALIAS_LINE="alias uplifted='$INSTALL_DIR/venv/bin/python -m server.run_main_server'"

    if ! grep -q "alias uplifted=" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Uplifted" >> "$SHELL_RC"
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
        log_success "Added to $SHELL_RC"
        log_info "Run 'source $SHELL_RC' or restart your shell"
    else
        log_info "Already in PATH"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Installation Directory:${NC} $INSTALL_DIR"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  1. Edit configuration: ${YELLOW}nano $INSTALL_DIR/.env${NC}"
    echo -e "  2. Add your API keys (OpenAI, Anthropic, etc.)"
    echo -e "  3. Start server: ${YELLOW}cd $INSTALL_DIR && ./start.sh${NC}"
    echo -e "  4. Access API: ${YELLOW}http://localhost:7541${NC}"
    echo -e "  5. API Docs: ${YELLOW}http://localhost:7541/docs${NC}"
    echo ""
    echo -e "${CYAN}Management Commands:${NC}"
    echo -e "  Start: ${YELLOW}$INSTALL_DIR/start.sh${NC}"
    echo -e "  Stop: ${YELLOW}$INSTALL_DIR/stop.sh${NC}"
    echo -e "  Status: ${YELLOW}$INSTALL_DIR/status.sh${NC}"

    if [ "$OS" = "linux" ] && [ -f "/etc/systemd/system/uplifted.service" ]; then
        echo ""
        echo -e "${CYAN}Systemd Service:${NC}"
        echo -e "  Start: ${YELLOW}sudo systemctl start uplifted${NC}"
        echo -e "  Stop: ${YELLOW}sudo systemctl stop uplifted${NC}"
        echo -e "  Status: ${YELLOW}sudo systemctl status uplifted${NC}"
        echo -e "  Logs: ${YELLOW}sudo journalctl -u uplifted -f${NC}"
    fi

    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo -e "  Configuration: $INSTALL_DIR/docs/CONFIG_MANAGEMENT.md"
    echo -e "  Deployment: $INSTALL_DIR/docs/DEPLOYMENT.md"
    echo -e "  API Usage: $INSTALL_DIR/examples/API_USAGE.md"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main installation flow
main() {
    print_banner

    log_info "Starting Uplifted installation..."
    echo ""

    detect_os
    check_root
    check_python
    install_system_deps
    setup_repository
    setup_python_env
    generate_config
    create_systemd_service
    create_launchers
    add_to_path

    print_summary
}

# Run main function
main "$@"
