# ============================================================================
# A-Maze-ing Generator - Makefile
# Maze generation using Prim's algorithm with configurable patterns
# ============================================================================

# ============================================================================
# Colors for output
# ============================================================================
RED       = \033[0;31m
GREEN     = \033[0;32m
YELLOW    = \033[0;33m
BLUE      = \033[0;34m
CYAN      = \033[0;36m
MAGENTA   = \033[0;35m
WHITE     = \033[1;37m
RESET     = \033[0m

# ============================================================================
# Project variables
# ============================================================================
NAME            = a-maze-ing
PYTHON          = python3
MAIN_FILE       = a_maze_ing.py
CONFIG_FILE     = config.txt
OUTPUT_FILE     = maze.txt
SEEDS_DIR       = seeds
VENV_DIR        = .venv
VENV_PYTHON     = $(VENV_DIR)/bin/python3
VENV_PIP        = $(VENV_DIR)/bin/pip3

# Prefer venv python if it exists (keeps tooling isolated/reproducible)
PYTHON_RUN      = $(shell [ -x $(VENV_PYTHON) ] && echo $(VENV_PYTHON) || echo $(PYTHON))

# ============================================================================
# Files to check/lint
# ============================================================================
PY_FILES        = a_maze_ing.py output_validator.py
LINT_TARGET     = a_maze_ing.py

# ============================================================================
# Default target
# ============================================================================
.DEFAULT_GOAL := run

# ============================================================================
# Main targets
# ============================================================================

all: $(NAME)
	@echo "$(GREEN)✓ A-Maze-ing is ready!$(RESET)"

$(NAME): $(MAIN_FILE)
	@echo "$(CYAN)Building $(NAME)...$(RESET)"
	@$(PYTHON) -m py_compile $(MAIN_FILE)
	@echo "$(GREEN)✓ Build successful$(RESET)"

# ============================================================================
# Run targets
# ============================================================================

run: $(NAME)
	@echo "$(CYAN)Running $(NAME)...$(RESET)"
	@$(PYTHON) $(MAIN_FILE)

debug: $(NAME)
	@echo "$(CYAN)Running in debug mode...$(RESET)"
	@$(PYTHON) -m pdb $(MAIN_FILE)

help:
	@echo "$(CYAN)=== A-Maze-ing Makefile Targets ===$(RESET)"
	@echo "$(GREEN)all$(RESET)        - Compile and verify the project"
	@echo "$(GREEN)run$(RESET)        - Execute the maze generator"
	@echo "$(GREEN)debug$(RESET)      - Run with Python debugger"
	@echo "$(GREEN)lint$(RESET)       - Check code style with flake8"
	@echo "$(GREEN)lint-strict$(RESET) - Strict flake8 checks"
	@echo "$(GREEN)clean$(RESET)      - Remove generated files and cache"
	@echo "$(GREEN)fclean$(RESET)     - Complete clean (includes seeds)"
	@echo "$(GREEN)re$(RESET)         - Clean and rebuild"
	@echo "$(GREEN)test$(RESET)       - Run output validator"
	@echo "$(GREEN)format$(RESET)     - Format code with autopep8"
	@echo "$(GREEN)install$(RESET)    - Install dependencies"
	@echo "$(GREEN)venv$(RESET)       - Create virtual environment"
	@echo "$(GREEN)help$(RESET)       - Show this help message"

# ============================================================================
# Code quality targets
# ============================================================================

lint:
	@echo "$(CYAN)Running flake8 linter...$(RESET)"
	@$(PYTHON_RUN) -m flake8 $(LINT_TARGET) || ( \
		echo "$(YELLOW)flake8 not installed. Run: make install (system) or make venv && source $(VENV_DIR)/bin/activate$(RESET)"; \
		exit 1; \
	)
	@echo "$(CYAN)Running mypy with mandatory flags...$(RESET)"
	@$(PYTHON_RUN) -m mypy --version >/dev/null 2>&1 || ( \
		echo "$(YELLOW)mypy not installed. Run: make install (system) or make venv && source $(VENV_DIR)/bin/activate$(RESET)"; \
		exit 1; \
	)
	@$(PYTHON_RUN) -m mypy $(LINT_TARGET) \
		--exclude '^mlx/' \
		--follow-imports=skip \
		--ignore-missing-imports \
		--allow-untyped-defs \
		--allow-untyped-calls \
		--allow-subclassing-any \
		--allow-any-generics \
		--disable-error-code=var-annotated \
		--disable-error-code=assignment \
		--disable-error-code=arg-type \
		--disable-error-code=index
	@echo "$(GREEN)✓ Linting complete$(RESET)"

lint-strict:
	@echo "$(CYAN)Running strict flake8 checks...$(RESET)"
	@$(PYTHON_RUN) -m flake8 $(LINT_TARGET)
	@echo "$(CYAN)Running mypy --strict...$(RESET)"
	@$(PYTHON_RUN) -m mypy --strict $(LINT_TARGET) \
		--exclude '^mlx/' \
		--follow-imports=skip
	@echo "$(GREEN)✓ Strict linting complete$(RESET)"

format:
	@echo "$(CYAN)Formatting code with autopep8...$(RESET)"
	@$(PYTHON_RUN) -m autopep8 --in-place --aggressive --aggressive $(LINT_TARGET)
	@echo "$(GREEN)✓ Formatting complete$(RESET)"

# ============================================================================
# Testing targets
# ============================================================================

test: $(NAME)
	@echo "$(CYAN)Running maze validation tests...$(RESET)"
	@if [ -f "$(OUTPUT_FILE)" ]; then \
		$(PYTHON) output_validator.py $(OUTPUT_FILE); \
		echo "$(GREEN)✓ Validation complete$(RESET)"; \
	else \
		echo "$(RED)✗ Error: $(OUTPUT_FILE) not found$(RESET)"; \
		echo "$(YELLOW)  Run 'make run' first to generate maze.txt$(RESET)"; \
		exit 1; \
	fi

check-syntax:
	@echo "$(CYAN)Checking Python syntax...$(RESET)"
	@for file in $(PY_FILES); do \
		if [ -f "$$file" ]; then \
			$(PYTHON) -m py_compile "$$file" && \
			echo "$(GREEN)✓$$file$(RESET)" || \
			echo "$(RED)✗ Syntax error in $$file$(RESET)"; \
		fi; \
	done

# ============================================================================
# Dependency management
# ============================================================================

install:
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install flake8 mypy autopep8
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

venv:
	@echo "$(CYAN)Creating virtual environment...$(RESET)"
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_PIP) install --upgrade pip
	@$(VENV_PIP) install flake8 mypy autopep8
	@echo "$(GREEN)✓ Virtual environment created$(RESET)"
	@echo "$(CYAN)Activate with: source $(VENV_DIR)/bin/activate$(RESET)"

# ============================================================================
# Cleaning targets
# ============================================================================

clean:
	@echo "$(CYAN)Cleaning up...$(RESET)"
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .mypy_cache
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@find . -type f -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage .pytest_cache
	@echo "$(GREEN)✓ Cache cleaned$(RESET)"

fclean: clean
	@echo "$(CYAN)Full clean (including seeds)...$(RESET)"
	@rm -rf $(SEEDS_DIR)/* 2>/dev/null || true
	@rm -rf $(SEEDS_DIR) || true
	@rm -f $(OUTPUT_FILE) maze_*.txt
	@rm -rf $(VENV_DIR)
	@echo "$(GREEN)✓ Full clean complete$(RESET)"

re: fclean all
	@echo "$(GREEN)✓ Rebuild complete$(RESET)"

# ============================================================================
# Documentation targets
# ============================================================================

info:
	@echo "$(CYAN)=== Project Information ===$(RESET)"
	@echo "$(WHITE)Name:$(RESET)           $(NAME)"
	@echo "$(WHITE)Main File:$(RESET)      $(MAIN_FILE)"
	@echo "$(WHITE)Config:$(RESET)         $(CONFIG_FILE)"
	@echo "$(WHITE)Output:$(RESET)         $(OUTPUT_FILE)"
	@echo "$(WHITE)Seeds Directory:$(RESET) $(SEEDS_DIR)"
	@echo "$(CYAN)=== Available Rules ===$(RESET)"
	@make -qp | awk -F':' '/^[a-zA-Z0-9_-]+:/ {print $$1}' | sort | uniq

# ============================================================================
# Phony targets (don't represent files)
# ============================================================================

.PHONY: all run debug lint lint-strict format clean fclean re help \
        install venv test check-syntax info

# ============================================================================
# Silent targets (for internal use)
# ============================================================================

.SILENT: check-syntax

# ============================================================================
# End of Makefile
# ============================================================================
