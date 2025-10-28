#!/usr/bin/env python3
"""
Uplifted Configuration Wizard

Interactive configuration wizard for first-time setup of Uplifted.
Guides users through environment detection, dependency checking,
and configuration file generation.

Usage:
    python config_wizard.py
    python config_wizard.py --non-interactive  # Use defaults
    python config_wizard.py --profile=production  # Use preset profile
"""

import argparse
import getpass
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    @classmethod
    def disable(cls):
        """Disable colors for non-terminal output."""
        cls.HEADER = ""
        cls.OKBLUE = ""
        cls.OKCYAN = ""
        cls.OKGREEN = ""
        cls.WARNING = ""
        cls.FAIL = ""
        cls.ENDC = ""
        cls.BOLD = ""
        cls.UNDERLINE = ""


class ConfigWizard:
    """Interactive configuration wizard for Uplifted."""

    def __init__(self, non_interactive: bool = False, profile: Optional[str] = None):
        """
        Initialize configuration wizard.

        Args:
            non_interactive: Skip prompts and use defaults
            profile: Preset configuration profile (development, production, minimal)
        """
        self.non_interactive = non_interactive
        self.profile = profile or "development"
        self.config_data: Dict[str, Any] = {}
        self.env_data: Dict[str, str] = {}

        # Detect if running in terminal
        if not sys.stdout.isatty() or os.getenv("NO_COLOR"):
            Colors.disable()

        # Project paths
        self.project_root = Path(__file__).parent.resolve()
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.plugins_dir = self.project_root / "plugins"

    def print_banner(self):
        """Print welcome banner."""
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}")
        print("    _   _       _ _  __ _           _ ")
        print("   | | | |_ __ | (_)/ _| |_ ___  __| |")
        print("   | | | | '_ \\| | | |_| __/ _ \\/ _` |")
        print("   | |_| | |_) | | |  _| ||  __/ (_| |")
        print("    \\___/| .__/|_|_|_|  \\__\\___|\\__,_|")
        print("         |_|                           ")
        print(f"{Colors.ENDC}")
        print(f"{Colors.BOLD}Configuration Wizard{Colors.ENDC}\n")
        print("This wizard will guide you through the initial setup of Uplifted.")
        print("You can press Ctrl+C at any time to cancel.\n")

    def log_info(self, message: str):
        """Print info message."""
        print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {message}")

    def log_success(self, message: str):
        """Print success message."""
        print(f"{Colors.OKGREEN}[✓]{Colors.ENDC} {message}")

    def log_warning(self, message: str):
        """Print warning message."""
        print(f"{Colors.WARNING}[!]{Colors.ENDC} {message}")

    def log_error(self, message: str):
        """Print error message."""
        print(f"{Colors.FAIL}[✗]{Colors.ENDC} {message}")

    def log_step(self, step: int, total: int, message: str):
        """Print step message."""
        print(f"\n{Colors.HEADER}[Step {step}/{total}]{Colors.ENDC} {Colors.BOLD}{message}{Colors.ENDC}")

    def prompt(self, question: str, default: Optional[str] = None, password: bool = False) -> str:
        """
        Prompt user for input.

        Args:
            question: Question to ask
            default: Default value if user presses Enter
            password: Hide input for passwords

        Returns:
            User input or default value
        """
        if self.non_interactive:
            return default or ""

        prompt_text = question
        if default:
            prompt_text += f" [{default}]"
        prompt_text += ": "

        if password:
            value = getpass.getpass(prompt_text)
        else:
            value = input(prompt_text).strip()

        return value if value else (default or "")

    def prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """
        Prompt user for yes/no confirmation.

        Args:
            question: Question to ask
            default: Default answer

        Returns:
            True for yes, False for no
        """
        if self.non_interactive:
            return default

        default_str = "Y/n" if default else "y/N"
        response = self.prompt(f"{question} ({default_str})", "y" if default else "n").lower()
        return response in ("y", "yes", "true", "1") if response else default

    def detect_system_info(self) -> Dict[str, Any]:
        """
        Detect system information.

        Returns:
            Dictionary containing system information
        """
        self.log_step(1, 6, "Detecting system environment")

        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count() or 1,
        }

        self.log_info(f"Operating System: {info['os']} ({info['architecture']})")
        self.log_info(f"Python Version: {info['python_version']}")
        self.log_info(f"CPU Cores: {info['cpu_count']}")

        # Check Python version
        python_version = tuple(map(int, info["python_version"].split(".")[:2]))
        if python_version < (3, 10):
            self.log_error(f"Python 3.10 or higher is required. Found: {info['python_version']}")
            sys.exit(1)
        else:
            self.log_success("Python version check passed")

        return info

    def check_dependencies(self) -> Dict[str, bool]:
        """
        Check for required and optional dependencies.

        Returns:
            Dictionary mapping dependency names to availability
        """
        self.log_step(2, 6, "Checking dependencies")

        deps = {}

        # Check for Git
        deps["git"] = shutil.which("git") is not None
        if deps["git"]:
            try:
                git_version = subprocess.check_output(
                    ["git", "--version"], stderr=subprocess.STDOUT, text=True
                ).strip()
                self.log_success(f"Git: {git_version}")
            except subprocess.CalledProcessError:
                deps["git"] = False

        if not deps["git"]:
            self.log_warning("Git not found (optional for plugins)")

        # Check for required Python packages
        required_packages = [
            "fastapi",
            "uvicorn",
            "httpx",
            "pydantic",
            "mcp",
        ]

        for package in required_packages:
            try:
                __import__(package)
                deps[package] = True
                self.log_success(f"Python package: {package}")
            except ImportError:
                deps[package] = False
                self.log_warning(f"Python package missing: {package}")

        # Check for optional packages
        optional_packages = ["yaml", "redis", "psycopg2"]
        for package in optional_packages:
            try:
                __import__(package)
                deps[package] = True
                self.log_info(f"Optional package: {package} (available)")
            except ImportError:
                deps[package] = False

        return deps

    def suggest_configuration(self, system_info: Dict[str, Any]) -> Tuple[str, int, int]:
        """
        Suggest optimal configuration based on system resources.

        Args:
            system_info: System information from detect_system_info()

        Returns:
            Tuple of (environment, workers, port)
        """
        cpu_count = system_info["cpu_count"]

        # Suggest worker count (conservative: cpu_count / 2, min 2, max 8)
        suggested_workers = max(2, min(8, cpu_count // 2))

        # Suggest environment based on interactive mode
        suggested_env = self.profile if self.profile else "development"

        return suggested_env, suggested_workers, 7541

    def collect_basic_config(self, system_info: Dict[str, Any]):
        """
        Collect basic configuration from user.

        Args:
            system_info: System information
        """
        self.log_step(3, 6, "Basic configuration")

        env, workers, port = self.suggest_configuration(system_info)

        # Environment
        env_choice = self.prompt(
            "Select environment (development/production/minimal)",
            default=env
        ).lower()
        if env_choice not in ("development", "production", "minimal"):
            env_choice = env

        self.env_data["UPLIFTED_ENV"] = env_choice

        # Server configuration
        host = self.prompt("Server host", default="0.0.0.0")
        port_str = self.prompt("Server port", default=str(port))
        workers_str = self.prompt(f"Number of workers (suggested: {workers})", default=str(workers))

        self.env_data["UPLIFTED__SERVER__HOST"] = host
        self.env_data["UPLIFTED__SERVER__PORT"] = port_str
        self.env_data["UPLIFTED__SERVER__WORKERS"] = workers_str
        self.env_data["UPLIFTED__SERVER__LOG_LEVEL"] = "DEBUG" if env_choice == "development" else "INFO"

        # Tools server
        tools_port = self.prompt("Tools server port", default="8086")
        self.env_data["UPLIFTED__TOOLS_SERVER__PORT"] = tools_port
        self.env_data["UPLIFTED__TOOLS_SERVER__MCP_ENABLED"] = "true"

        self.log_success("Basic configuration collected")

    def collect_ai_providers(self):
        """Collect AI provider API keys."""
        self.log_step(4, 6, "AI Provider Configuration")

        print("\nAt least one AI provider API key is required.")
        print("You can add more later by editing the .env file.\n")

        providers = {
            "OpenAI": "OPENAI_API_KEY",
            "Anthropic Claude": "ANTHROPIC_API_KEY",
            "DeepSeek": "DEEPSEEK_API_KEY",
            "Google": "GOOGLE_GLA_API_KEY",
            "OpenRouter": "OPENROUTER_API_KEY",
        }

        has_any_key = False

        for provider_name, env_key in providers.items():
            if self.prompt_yes_no(f"Configure {provider_name}?", default=(provider_name == "OpenAI")):
                api_key = self.prompt(f"{provider_name} API Key", password=True)
                if api_key:
                    self.env_data[env_key] = api_key
                    has_any_key = True
                    self.log_success(f"{provider_name} API key saved")

        if not has_any_key and not self.non_interactive:
            self.log_warning("No AI provider API keys configured!")
            self.log_warning("You will need to add at least one API key to .env before starting the server.")

        # Azure OpenAI (more complex)
        if self.prompt_yes_no("Configure Azure OpenAI?", default=False):
            self.env_data["AZURE_OPENAI_ENDPOINT"] = self.prompt("Azure OpenAI Endpoint")
            self.env_data["AZURE_OPENAI_API_VERSION"] = self.prompt("API Version", default="2024-02-15-preview")
            self.env_data["AZURE_OPENAI_API_KEY"] = self.prompt("Azure OpenAI API Key", password=True)
            if self.env_data["AZURE_OPENAI_API_KEY"]:
                has_any_key = True
                self.log_success("Azure OpenAI configured")

        # AWS Bedrock
        if self.prompt_yes_no("Configure AWS Bedrock?", default=False):
            self.env_data["AWS_ACCESS_KEY_ID"] = self.prompt("AWS Access Key ID")
            self.env_data["AWS_SECRET_ACCESS_KEY"] = self.prompt("AWS Secret Access Key", password=True)
            self.env_data["AWS_REGION"] = self.prompt("AWS Region", default="us-east-1")
            if self.env_data["AWS_SECRET_ACCESS_KEY"]:
                has_any_key = True
                self.log_success("AWS Bedrock configured")

    def collect_additional_config(self):
        """Collect additional configuration options."""
        self.log_step(5, 6, "Additional configuration")

        # Database
        db_path = self.prompt("Database path", default="./data/uplifted.db")
        self.env_data["UPLIFTED__DATABASE__PATH"] = db_path

        # Plugins
        enable_plugins = self.prompt_yes_no("Enable plugins?", default=True)
        self.env_data["UPLIFTED__PLUGINS__ENABLED"] = "true" if enable_plugins else "false"
        if enable_plugins:
            self.env_data["UPLIFTED__PLUGINS__AUTO_LOAD"] = "true"
            self.env_data["UPLIFTED__PLUGINS__AUTO_ACTIVATE"] = "true"

        # Logging
        log_file = self.prompt("Log file path", default="./logs/uplifted.log")
        self.env_data["UPLIFTED__LOGGING__FILE"] = log_file
        self.env_data["UPLIFTED__LOGGING__LEVEL"] = self.env_data.get("UPLIFTED__SERVER__LOG_LEVEL", "INFO")

        # Security
        if self.prompt_yes_no("Enable API key authentication?", default=False):
            self.env_data["UPLIFTED__SECURITY__API_KEY_REQUIRED"] = "true"
            api_key = self.prompt("API Key (will be generated if empty)", password=True)
            if not api_key:
                import secrets
                api_key = secrets.token_urlsafe(32)
                self.log_info(f"Generated API key: {api_key}")
            self.env_data["UPLIFTED__SECURITY__API_KEY"] = api_key
        else:
            self.env_data["UPLIFTED__SECURITY__API_KEY_REQUIRED"] = "false"

        # CORS
        self.env_data["UPLIFTED__SECURITY__CORS_ENABLED"] = "true"
        self.env_data["UPLIFTED__SECURITY__CORS_ORIGINS"] = "*"

        # Rate limiting
        self.env_data["UPLIFTED__SECURITY__RATE_LIMIT__ENABLED"] = "true"
        self.env_data["UPLIFTED__SECURITY__RATE_LIMIT__REQUESTS_PER_MINUTE"] = "60"

        self.log_success("Additional configuration collected")

    def create_directories(self):
        """Create necessary directories."""
        directories = [
            self.config_dir,
            self.data_dir,
            self.logs_dir,
            self.plugins_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.log_info(f"Created directory: {directory}")

    def write_env_file(self):
        """Write environment variables to .env file."""
        env_file = self.project_root / ".env"

        # Check if .env already exists
        if env_file.exists():
            if not self.non_interactive:
                if not self.prompt_yes_no(f"{env_file} already exists. Overwrite?", default=False):
                    backup_file = self.project_root / ".env.backup"
                    shutil.copy(env_file, backup_file)
                    self.log_info(f"Backed up existing .env to {backup_file}")

        # Write .env file
        with open(env_file, "w") as f:
            f.write("# Uplifted Environment Variables\n")
            f.write(f"# Generated by config wizard on {platform.node()}\n")
            f.write("# DO NOT commit this file to version control!\n\n")

            sections = {
                "Server Configuration": [
                    "UPLIFTED_ENV",
                    "UPLIFTED__SERVER__HOST",
                    "UPLIFTED__SERVER__PORT",
                    "UPLIFTED__SERVER__WORKERS",
                    "UPLIFTED__SERVER__LOG_LEVEL",
                ],
                "Tools Server": [
                    "UPLIFTED__TOOLS_SERVER__PORT",
                    "UPLIFTED__TOOLS_SERVER__MCP_ENABLED",
                ],
                "Database": [
                    "UPLIFTED__DATABASE__PATH",
                ],
                "Plugins": [
                    "UPLIFTED__PLUGINS__ENABLED",
                    "UPLIFTED__PLUGINS__AUTO_LOAD",
                    "UPLIFTED__PLUGINS__AUTO_ACTIVATE",
                ],
                "Logging": [
                    "UPLIFTED__LOGGING__FILE",
                    "UPLIFTED__LOGGING__LEVEL",
                ],
                "Security": [
                    "UPLIFTED__SECURITY__API_KEY_REQUIRED",
                    "UPLIFTED__SECURITY__API_KEY",
                    "UPLIFTED__SECURITY__CORS_ENABLED",
                    "UPLIFTED__SECURITY__CORS_ORIGINS",
                    "UPLIFTED__SECURITY__RATE_LIMIT__ENABLED",
                    "UPLIFTED__SECURITY__RATE_LIMIT__REQUESTS_PER_MINUTE",
                ],
                "AI Providers": [
                    "OPENAI_API_KEY",
                    "ANTHROPIC_API_KEY",
                    "DEEPSEEK_API_KEY",
                    "GOOGLE_GLA_API_KEY",
                    "OPENROUTER_API_KEY",
                    "AZURE_OPENAI_ENDPOINT",
                    "AZURE_OPENAI_API_VERSION",
                    "AZURE_OPENAI_API_KEY",
                    "AWS_ACCESS_KEY_ID",
                    "AWS_SECRET_ACCESS_KEY",
                    "AWS_REGION",
                ],
            }

            for section, keys in sections.items():
                section_has_values = any(key in self.env_data for key in keys)
                if section_has_values:
                    f.write(f"# {section}\n")
                    for key in keys:
                        if key in self.env_data:
                            value = self.env_data[key]
                            f.write(f"{key}={value}\n")
                    f.write("\n")

        self.log_success(f"Environment file created: {env_file}")

    def write_config_yaml(self):
        """Write configuration to YAML file (if PyYAML available)."""
        if yaml is None:
            self.log_warning("PyYAML not installed, skipping config.yaml generation")
            return

        config_file = self.config_dir / "config.yaml"

        # Use the config_utils if available
        try:
            from server.uplifted.extensions.config_utils import generate_config_template

            env = self.env_data.get("UPLIFTED_ENV", "development")
            generate_config_template(env, str(config_file))
            self.log_success(f"Configuration file created: {config_file}")
        except ImportError:
            self.log_warning("config_utils not available, using basic YAML generation")

            # Basic YAML generation
            config = {
                "server": {
                    "host": self.env_data.get("UPLIFTED__SERVER__HOST", "0.0.0.0"),
                    "port": int(self.env_data.get("UPLIFTED__SERVER__PORT", "7541")),
                    "workers": int(self.env_data.get("UPLIFTED__SERVER__WORKERS", "4")),
                },
                "plugins": {
                    "enabled": self.env_data.get("UPLIFTED__PLUGINS__ENABLED", "true") == "true",
                    "auto_load": True,
                },
                "logging": {
                    "level": self.env_data.get("UPLIFTED__LOGGING__LEVEL", "INFO"),
                    "file": self.env_data.get("UPLIFTED__LOGGING__FILE", "./logs/uplifted.log"),
                },
            }

            with open(config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self.log_success(f"Configuration file created: {config_file}")

    def generate_files(self):
        """Generate configuration files."""
        self.log_step(6, 6, "Generating configuration files")

        self.create_directories()
        self.write_env_file()
        self.write_config_yaml()

    def print_next_steps(self):
        """Print next steps for the user."""
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}  Configuration Complete!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

        print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}\n")

        env = self.env_data.get("UPLIFTED_ENV", "development")
        port = self.env_data.get("UPLIFTED__SERVER__PORT", "7541")
        tools_port = self.env_data.get("UPLIFTED__TOOLS_SERVER__PORT", "8086")

        if env == "development":
            print("1. Review and edit configuration:")
            print(f"   {Colors.OKCYAN}nano .env{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}nano config/config.yaml{Colors.ENDC}\n")

            print("2. Install dependencies (if not already installed):")
            print(f"   {Colors.OKCYAN}python -m venv venv{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}source venv/bin/activate{Colors.ENDC}  # On Windows: venv\\Scripts\\activate")
            print(f"   {Colors.OKCYAN}pip install uv && uv pip install -e .{Colors.ENDC}\n")

            print("3. Start the development server:")
            print(f"   {Colors.OKCYAN}python -m server.run_main_server{Colors.ENDC}\n")

        else:  # production or minimal
            print("1. Install dependencies:")
            print(f"   {Colors.OKCYAN}python -m venv venv{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}source venv/bin/activate{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}pip install uv && uv pip install -e .{Colors.ENDC}\n")

            system = platform.system()
            if system == "Linux":
                print("2. Install as systemd service (optional):")
                print(f"   {Colors.OKCYAN}sudo cp systemd/uplifted.service /etc/systemd/system/{Colors.ENDC}")
                print(f"   {Colors.OKCYAN}sudo systemctl daemon-reload{Colors.ENDC}")
                print(f"   {Colors.OKCYAN}sudo systemctl enable uplifted{Colors.ENDC}")
                print(f"   {Colors.OKCYAN}sudo systemctl start uplifted{Colors.ENDC}\n")

                print("3. Or run with launcher script:")
                print(f"   {Colors.OKCYAN}./start.sh{Colors.ENDC}\n")

            elif system == "Windows":
                print("2. Run with launcher script:")
                print(f"   {Colors.OKCYAN}.\\start.bat{Colors.ENDC}\n")

                print("   Or install as Windows Service (requires NSSM):\n")
            else:
                print("2. Start the server:")
                print(f"   {Colors.OKCYAN}python -m server.run_main_server{Colors.ENDC}\n")

        print(f"{Colors.BOLD}Access URLs:{Colors.ENDC}")
        print(f"   Main API:    {Colors.OKCYAN}http://localhost:{port}{Colors.ENDC}")
        print(f"   API Docs:    {Colors.OKCYAN}http://localhost:{port}/docs{Colors.ENDC}")
        print(f"   Tools Server: {Colors.OKCYAN}http://localhost:{tools_port}{Colors.ENDC}\n")

        print(f"{Colors.BOLD}Documentation:{Colors.ENDC}")
        print(f"   Configuration: {Colors.OKCYAN}docs/CONFIG_MANAGEMENT.md{Colors.ENDC}")
        print(f"   Deployment:    {Colors.OKCYAN}docs/DEPLOYMENT.md{Colors.ENDC}")
        print(f"   Plugins:       {Colors.OKCYAN}examples/plugins/{Colors.ENDC}\n")

        print(f"{Colors.OKGREEN}{'=' * 60}{Colors.ENDC}\n")

    def run(self):
        """Run the configuration wizard."""
        try:
            self.print_banner()

            system_info = self.detect_system_info()
            self.check_dependencies()
            self.collect_basic_config(system_info)
            self.collect_ai_providers()
            self.collect_additional_config()
            self.generate_files()

            self.print_next_steps()

        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Configuration cancelled by user.{Colors.ENDC}")
            sys.exit(1)
        except Exception as e:
            self.log_error(f"An error occurred: {e}")
            if os.getenv("DEBUG"):
                raise
            sys.exit(1)


def main():
    """Main entry point for configuration wizard."""
    parser = argparse.ArgumentParser(
        description="Uplifted Configuration Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode using defaults",
    )
    parser.add_argument(
        "--profile",
        choices=["development", "production", "minimal"],
        default="development",
        help="Configuration profile to use",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    wizard = ConfigWizard(
        non_interactive=args.non_interactive,
        profile=args.profile,
    )
    wizard.run()


if __name__ == "__main__":
    main()
