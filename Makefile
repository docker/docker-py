.PHONY: all build test integration-test unit-test

HOST_TMPDIR=test -n "$(TMPDIR)" && echo $(TMPDIR) || echo /tmp

all: test

build:
	docker build -t docker-py .

test: unit-test integration-test

unit-test: build
	docker run docker-py python tests/test.py

integration-test: build
	docker run -e NOT_ON_HOST=true -v `$(HOST_TMPDIR)`:/tmp -v /var/run/docker.sock:/var/run/docker.sock docker-py python tests/integration_test.py
