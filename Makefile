install:
	#install commands
	pip install --upgrade pip &&\
	pip install -r requirements.txt
format:
	#format code
	black *.py shared_code/*.py
lint:
	#pylint with no refactor or convention msg's
	pylint --errors-only --disable=no-self-argument --extension-pkg-whitelist='pydantic' *.py shared_code/*.py
test:
	#test
	python -m pytest -vv --cov=shared_code test_api_get.py
build:
    #build container
deploy:
	#deploy
all: install format lint test deploy