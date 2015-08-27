.PHONY: all build test integration-test unit-test build-py3 unit-test-py3 integration-test-py3

HOST_TMPDIR=test -n "$(TMPDIR)" && echo $(TMPDIR) || echo /tmp

all: test

build:
	docker build -t docker-py .

build-py3:
	docker build -t docker-py3 -f Dockerfile-py3 .

test: unit-test integration-test unit-test-py3 integration-test-py3

unit-test: build
	docker run docker-py py.test tests/test.py tests/utils_test.py

unit-test-py3: build-py3
	docker run docker-py3 py.test tests/test.py tests/utils_test.py

integration-test: build
	docker version
	docker run -v `$(HOST_TMPDIR)`:/tmp -v /var/run/docker.sock:/var/run/docker.sock docker-py py.test -rxs tests/integration_test.py

integration-test-py3: build-py3
	docker version
	docker run -v `$(HOST_TMPDIR)`:/tmp -v /var/run/docker.sock:/var/run/docker.sock docker-py3 py.test -rxs tests/integration_test.py
