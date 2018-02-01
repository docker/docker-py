.PHONY: all
all: test

.PHONY: clean
clean:
	-docker rm -f dpy-dind-py2 dpy-dind-py3
	find -name "__pycache__" | xargs rm -rf

.PHONY: build
build:
	docker build -t docker-sdk-python .

.PHONY: build-py3
build-py3:
	docker build -t docker-sdk-python3 -f Dockerfile-py3 .

.PHONY: build-docs
build-docs:
	docker build -t docker-sdk-python-docs -f Dockerfile-docs --build-arg uid=$(shell id -u) --build-arg gid=$(shell id -g) .

.PHONY: build-dind-certs
build-dind-certs:
	docker build -t dpy-dind-certs -f tests/Dockerfile-dind-certs .

.PHONY: test
test: flake8 unit-test unit-test-py3 integration-dind integration-dind-ssl

.PHONY: unit-test
unit-test: build
	docker run -t --rm docker-sdk-python py.test tests/unit

.PHONY: unit-test-py3
unit-test-py3: build-py3
	docker run -t --rm docker-sdk-python3 py.test tests/unit

.PHONY: integration-test
integration-test: build
	docker run -t --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python py.test -v tests/integration/${file}

.PHONY: integration-test-py3
integration-test-py3: build-py3
	docker run -t --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 py.test tests/integration/${file}

TEST_API_VERSION ?= 1.35
TEST_ENGINE_VERSION ?= 17.12.0-ce

.PHONY: integration-dind
integration-dind: integration-dind-py2 integration-dind-py3

.PHONY: integration-dind-py2
integration-dind-py2: build
	docker rm -vf dpy-dind-py2 || :
	docker run -d --name dpy-dind-py2 --privileged dockerswarm/dind:${TEST_ENGINE_VERSION} dockerd\
		-H tcp://0.0.0.0:2375 --experimental
	docker run -t --rm --env="DOCKER_HOST=tcp://docker:2375" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--link=dpy-dind-py2:docker docker-sdk-python py.test tests/integration
	docker rm -vf dpy-dind-py2

.PHONY: integration-dind-py3
integration-dind-py3: build-py3
	docker rm -vf dpy-dind-py3 || :
	docker run -d --name dpy-dind-py3 --privileged dockerswarm/dind:${TEST_ENGINE_VERSION} dockerd\
		-H tcp://0.0.0.0:2375 --experimental
	docker run -t --rm --env="DOCKER_HOST=tcp://docker:2375" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--link=dpy-dind-py3:docker docker-sdk-python3 py.test tests/integration
	docker rm -vf dpy-dind-py3

.PHONY: integration-dind-ssl
integration-dind-ssl: build-dind-certs build build-py3
	docker run -d --name dpy-dind-certs dpy-dind-certs
	docker run -d --env="DOCKER_HOST=tcp://localhost:2375" --env="DOCKER_TLS_VERIFY=1"\
		--env="DOCKER_CERT_PATH=/certs" --volumes-from dpy-dind-certs --name dpy-dind-ssl\
		-v /tmp --privileged dockerswarm/dind:${TEST_ENGINE_VERSION} dockerd --tlsverify\
		--tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem\
		--tlskey=/certs/server-key.pem -H tcp://0.0.0.0:2375 --experimental
	docker run -t --rm --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--link=dpy-dind-ssl:docker docker-sdk-python py.test tests/integration
	docker run -t --rm --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--link=dpy-dind-ssl:docker docker-sdk-python3 py.test tests/integration
	docker rm -vf dpy-dind-ssl dpy-dind-certs

.PHONY: flake8
flake8: build
	docker run -t --rm docker-sdk-python flake8 docker tests

.PHONY: docs
docs: build-docs
	docker run --rm -t -v `pwd`:/src docker-sdk-python-docs sphinx-build docs docs/_build

.PHONY: shell
shell: build
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python python
