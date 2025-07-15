.PHONY: up down rebuild logs dbinit
 
up:
	docker-compose up --build

down:
	docker-compose down

rebuild:
	docker-compose down
	docker-compose up --build --force-recreate

logs:
	docker-compose logs -f

dbinit:
	docker-compose exec backend python database/db_init.py