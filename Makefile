.PHONY: setup dev register scan report cloud-status up-db down-db api web test-api test-web test

setup:
	./scripts/edge setup

dev:
	./scripts/edge dev

register:
	./scripts/edge register

scan:
	./scripts/edge scan $(CIDR)

report:
	./scripts/edge report

cloud-status:
	./scripts/edge status --cloud

status:
	./scripts/edge status

up-db:
	./scripts/edge db

down-db:
	./scripts/edge stop-db

api:
	./scripts/edge api

web:
	./scripts/edge web

test-api:
	PYTHONPATH=api:agent pytest tests

test-web:
	cd web && npm test -- --run

test:
	./scripts/edge test
