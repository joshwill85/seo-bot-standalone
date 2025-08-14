# SEO Bot Development Commands

.PHONY: help install dev test build clean lint

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev: ## Start development servers
	@echo "Starting backend and frontend development servers..."
	@echo "Backend: cd backend && python -m seo_bot.cli --help"
	@echo "Frontend: cd frontend && npm run dev"

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/
	@echo "Running frontend tests..."
	cd frontend && npm run test

build: ## Build all projects
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Building backend..."
	cd backend && pip install -e .

lint: ## Run linting on all projects
	@echo "Linting backend..."
	cd backend && ruff check . && black --check .
	@echo "Linting frontend..."
	cd frontend && npm run lint

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf frontend/dist/
	rm -rf frontend/node_modules/
	rm -rf backend/dist/
	rm -rf backend/.pytest_cache/
	find . -type d -name "__pycache__" -delete

docker-build: ## Build Docker containers
	cd infrastructure/docker && docker-compose build

docker-up: ## Start Docker services
	cd infrastructure/docker && docker-compose up -d

docker-down: ## Stop Docker services
	cd infrastructure/docker && docker-compose down