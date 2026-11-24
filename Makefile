.PHONY: up down reset logs lint

up:
	git config core.hooksPath .githooks
	docker compose up -d --wait

down:
	docker compose down

reset:
	docker compose down -v

logs:
	docker compose logs -f

lint:
	docker compose run --rm -T tools check .
	docker compose run --rm -T tools format --check .
