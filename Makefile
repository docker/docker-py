.PHONY: all build test integration-test unit-test

all: test

build:
	docker build -t docker-py .

test: unit-test integration-test

unit-test: build
	docker run docker-py python tests/test.py

integration-test: build
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py python tests/integration_test.py

