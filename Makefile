PYTHON ?= python3
FRONTEND_DIR := web/frontend

.PHONY: dev api frontend build-frontend

dev:
	./web/dev.sh

api:
	uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd $(FRONTEND_DIR) && npm install && npm run dev -- --host

build-frontend:
	cd $(FRONTEND_DIR) && npm install && npm run build
