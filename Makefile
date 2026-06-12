.PHONY: setup pipeline dashboard

VENV = .venv
PYTHON = $(VENV)/bin/python
STREAMLIT = $(VENV)/bin/streamlit
PIP = $(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) analysis.py

dashboard:
	$(STREAMLIT) run dashboard.py