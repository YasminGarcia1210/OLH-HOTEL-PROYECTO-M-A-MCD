PYTHON ?= .venv/bin/python
PIP    ?= .venv/bin/pip

.PHONY: help install run run-dev check

help:
	@echo "Available commands:"
	@echo "  make install   Create venv and install dependencies"
	@echo "  make run       Start the ABSA API"
	@echo "  make run-dev   Start the ABSA API in development mode"
	@echo "  make check     Validate Python source files"

install:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) app.py

run-dev:
	FLASK_ENV=development FLASK_DEBUG=1 $(PYTHON) app.py

check:
	$(PYTHON) -m py_compile app.py config.py db.py routes/absa.py services/absa_service.py
