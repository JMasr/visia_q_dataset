#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = visia_q_dataset
PYTHON_VERSION = 3.10
PYTHON_INTERPRETER = ./.venv/bin/python

#################################################################################
# COMMANDS                                                                      #
#################################################################################


## Install Python dependencies
.PHONY: requirements
requirements:
	uv sync
	



## Delete all compiled Python files
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete


## Lint using ruff (use `make format` to do formatting)
.PHONY: lint
lint:
	ruff format --check
	ruff check

## Format source code with ruff
.PHONY: format
format:
	ruff check --fix
	ruff format



## Run tests (integration tests skipped; no raw dataset needed)
.PHONY: test
test: requirements
	$(PYTHON_INTERPRETER) -m pytest tests -m "not integration"

## Run integration tests (requires data/raw/visia_q_dataset.csv)
.PHONY: test-integration
test-integration: requirements
	$(PYTHON_INTERPRETER) -m pytest tests -m integration

## Run all tests including integration
.PHONY: test-all
test-all: requirements
	$(PYTHON_INTERPRETER) -m pytest tests


## Set up Python interpreter environment
.PHONY: create_environment
create_environment:
	uv venv --python $(PYTHON_VERSION)
	@echo ">>> New uv virtual environment created. Activate with:"
	@echo ">>> Windows: .\\\\.venv\\\\Scripts\\\\activate"
	@echo ">>> Unix/macOS: source ./.venv/bin/activate"
	



#################################################################################
# PROJECT RULES                                                                 #
#################################################################################


## Make dataset
.PHONY: data
data: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.dataset filter-all-valid

## Make dataset with Oviedo negative + MACI valid
.PHONY: data_ov_maci_valid
data_ov_maci_valid: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.dataset filter-all-valid

## Make dataset with only Oviedo negative
.PHONY: data_ov_neg
data_ov_neg: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.dataset filter-oviedo-negative

## Make dataset with only MACI valid
.PHONY: data_maci_valid
data_maci_valid: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.dataset filter-maci-valid

## Calculate reliability and normality metrics
.PHONY: metrics
metrics: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.metrics run-metrics

## Compute descriptive statistics (mean, SD, median, min, max) per instrument per group
.PHONY: stats
stats: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.metrics descriptive-stats

## Reproduce and verify all numerical values reported in the paper
.PHONY: reproduce
reproduce: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.reproduce

## Build codebook with Spanish item texts from raw/visia_q_structure.json
.PHONY: codebook
codebook: requirements
	$(PYTHON_INTERPRETER) -m visia_q_dataset.codebook



#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('Available rules:\n'); \
print('\n'.join(['{:25}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@$(PYTHON_INTERPRETER) -c "${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)
