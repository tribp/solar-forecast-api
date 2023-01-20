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
	python -m pytest -vv --cov=shared_code --cov-report term-missing test_api.py
build:
    #build container - optional
	#docker build -t solar-forecast-api .
run:
    #run container - optional
	#docker run -p 8081:8080 -e OPENWEATHERMAP_API_KEY='<your API Key>' --name cont_SFA solar-forecast-api
deploy:
	#deploy

all: install format lint test deploy