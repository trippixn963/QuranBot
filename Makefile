# =============================================================================
# QuranBot - Makefile for Development and Deployment
# =============================================================================

.PHONY: help install install-dev test lint format clean run deploy-vps backup

# Default target
help:
	@echo "QuranBot - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run          - Run the bot locally"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  clean        - Clean up temporary files"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-vps   - Deploy to VPS"
	@echo "  backup       - Create backup of current state"
	@echo ""
	@echo "VPS Management:"
	@echo "  vps-start    - Start bot on VPS"
	@echo "  vps-stop     - Stop bot on VPS"
	@echo "  vps-restart  - Restart bot on VPS"
	@echo "  vps-status   - Check bot status on VPS"
	@echo "  vps-logs     - View bot logs on VPS"

# Installation
install:
	@echo "Installing production dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt

# Development
run:
	@echo "Starting QuranBot..."
	python run.py

test:
	@echo "Running tests..."
	pytest tests/ -v --cov=src --cov-report=html

lint:
	@echo "Running linting checks..."
	flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	black src/ --line-length=88
	isort src/ --profile=black

clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

# Deployment
deploy-vps:
	@echo "Deploying to VPS..."
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create it from env_template.txt"; \
		exit 1; \
	fi
	scp -r . root@159.89.90.90:/opt/quranbot/
	ssh root@159.89.90.90 "cd /opt/quranbot && chmod +x deploy_temp/setup_vps.sh && ./deploy_temp/setup_vps.sh"

backup:
	@echo "Creating backup..."
	@timestamp=$$(date +"%Y-%m-%d_%H-%M-%S"); \
	backup_dir="backup/QuranBot_v$$(grep 'version=' setup.py | cut -d'"' -f2)_$$timestamp"; \
	mkdir -p "$$backup_dir"; \
	cp -r src/ "$$backup_dir/"; \
	cp -r scripts/ "$$backup_dir/"; \
	cp *.py "$$backup_dir/"; \
	cp *.txt "$$backup_dir/"; \
	cp *.md "$$backup_dir/"; \
	cp Makefile "$$backup_dir/"; \
	echo "Backup created: $$backup_dir"

# VPS Management
vps-start:
	@echo "Starting bot on VPS..."
	./scripts/vps/start_bot.sh

vps-stop:
	@echo "Stopping bot on VPS..."
	./scripts/vps/stop_bot.sh

vps-restart:
	@echo "Restarting bot on VPS..."
	./scripts/vps/restart_bot.sh

vps-status:
	@echo "Checking bot status on VPS..."
	./scripts/vps/status_bot.sh

vps-logs:
	@echo "Viewing bot logs on VPS..."
	./scripts/vps/logs_bot.sh

# Development setup
setup-dev: install-dev
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp env_template.txt .env; \
		echo "Created .env file from template. Please edit it with your configuration."; \
	else \
		echo ".env file already exists."; \
	fi
	@echo "Development setup complete!"

# Quick start
quick-start: install setup-dev
	@echo "Quick start setup complete!"
	@echo "Next steps:"
	@echo "1. Edit .env file with your Discord bot configuration"
	@echo "2. Add audio files to the audio/ directory"
	@echo "3. Run 'make run' to start the bot" 