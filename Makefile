install:
	#install commands
	pip install --upgrade pip &&\
	pip install -r requirements.txt
format:
	#format code
	black *.py shared_code/*.py
lint:
	#pylint
test:
	#test
deploy:
	#deploy
all: install format lint test deploy