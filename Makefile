TEST_API_VERSION ?= 1.41
TEST_ENGINE_VERSION ?= 20.10.05

.PHONY: all
all: test

.PHONY: clean
clean:
	-docker rm -f dpy-dind-py3 dpy-dind-certs dpy-dind-ssl
	find -name "__pycache__" | xargs rm -rf

.PHONY: build-dind-ssh
build-dind-ssh:
	docker build -t docker-dind-ssh -f tests/Dockerfile-ssh-dind --build-arg ENGINE_VERSION=${TEST_ENGINE_VERSION} --build-arg API_VERSION=${TEST_API_VERSION} --build-arg APT_MIRROR .

.PHONY: build-py3
build-py3:
	docker build -t docker-sdk-python3 -f tests/Dockerfile --build-arg APT_MIRROR .

.PHONY: build-docs
build-docs:
	docker build -t docker-sdk-python-docs -f Dockerfile-docs --build-arg uid=$(shell id -u) --build-arg gid=$(shell id -g) .

.PHONY: build-dind-certs
build-dind-certs:
	docker build -t dpy-dind-certs -f tests/Dockerfile-dind-certs .

.PHONY: test
test: flake8 unit-test-py3 integration-dind integration-dind-ssl

.PHONY: unit-test-py3
unit-test-py3: build-py3
	docker run -t --rm docker-sdk-python3 py.test tests/unit

.PHONY: integration-test-py3
integration-test-py3: build-py3
	docker run -t --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 py.test -v tests/integration/${file}

.PHONY: setup-network
setup-network:
	docker network inspect dpy-tests || docker network create dpy-tests

.PHONY: integration-dind
integration-dind: integration-dind-py3

.PHONY: integration-dind-py3
integration-dind-py3: build-py3 setup-network
	docker rm -vf dpy-dind-py3 || :
	docker run -d --network dpy-tests --name dpy-dind-py3 --privileged\
		docker:${TEST_ENGINE_VERSION}-dind dockerd -H tcp://0.0.0.0:2375 --experimental
	docker run -t --rm --env="DOCKER_HOST=tcp://dpy-dind-py3:2375" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--network dpy-tests docker-sdk-python3 py.test tests/integration/${file}
	docker rm -vf dpy-dind-py3


.PHONY: integration-ssh-py3
integration-ssh-py3: build-dind-ssh build-py3 setup-network
	docker rm -vf dpy-dind-py3 || :
	docker run -d --network dpy-tests --name dpy-dind-py3 --privileged\
		docker-dind-ssh dockerd --experimental
	# start SSH daemon
	docker exec dpy-dind-py3 sh -c "/usr/sbin/sshd"
	docker run -t --rm --env="DOCKER_HOST=ssh://dpy-dind-py3" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--network dpy-tests docker-sdk-python3 py.test tests/ssh/${file}
	docker rm -vf dpy-dind-py3


.PHONY: integration-dind-ssl
integration-dind-ssl: build-dind-certs build-py3
	docker rm -vf dpy-dind-certs dpy-dind-ssl || :
	docker run -d --name dpy-dind-certs dpy-dind-certs
	docker run -d --env="DOCKER_HOST=tcp://localhost:2375" --env="DOCKER_TLS_VERIFY=1"\
		--env="DOCKER_CERT_PATH=/certs" --volumes-from dpy-dind-certs --name dpy-dind-ssl\
		--network dpy-tests --network-alias docker -v /tmp --privileged\
		docker:${TEST_ENGINE_VERSION}-dind\
		dockerd --tlsverify --tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem\
		--tlskey=/certs/server-key.pem -H tcp://0.0.0.0:2375 --experimental
	docker run -t --rm --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}"\
		--network dpy-tests docker-sdk-python3 py.test tests/integration/${file}
	docker rm -vf dpy-dind-ssl dpy-dind-certs

.PHONY: flake8
flake8: build-py3
	docker run -t --rm docker-sdk-python3 flake8 docker tests

.PHONY: docs
docs: build-docs
	docker run --rm -t -v `pwd`:/src docker-sdk-python-docs sphinx-build docs docs/_build

.PHONY: shell
shell: build-py3
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 python
