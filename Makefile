.PHONY: lint format install run migrations migrate

install:
	pip install -r requirements.txt

run:
	python manage.py runserver

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

# Ta procédure de commit : Toujours lancer ça avant !
lint:
	@echo "--- 1. Black (Formatage) ---"
	black . --check
	@echo "--- 2. Isort (Imports) ---"
	isort . --check-only
	@echo "--- 3. Flake8 (Qualité) ---"
	flake8 .
	@echo "✅ Code clean, prêt à commit !"

format:
	black .
	isort .
