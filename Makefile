TEST_API_VERSION ?= 1.45
TEST_ENGINE_VERSION ?= 26.1

ifeq ($(OS),Windows_NT)
    PLATFORM := Windows
else
    PLATFORM := $(shell sh -c 'uname -s 2>/dev/null || echo Unknown')
endif

ifeq ($(PLATFORM),Linux)
	uid_args := "--build-arg uid=$(shell id -u) --build-arg gid=$(shell id -g)"
endif

SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER ?= $(shell git describe --match '[0-9]*' --dirty='.m' --always --tags 2>/dev/null | sed -r 's/-([0-9]+)/.dev\1/' | sed 's/-/+/')
ifeq ($(SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER),)
	SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER = "dev"
endif

.PHONY: all
all: test

.PHONY: clean
clean:
	-docker rm -f dpy-dind dpy-dind-certs dpy-dind-ssl
	find -name "__pycache__" | xargs rm -rf

.PHONY: build-dind-ssh
build-dind-ssh:
	docker build \
		--pull \
		-t docker-dind-ssh \
		-f tests/Dockerfile-ssh-dind \
		--build-arg VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER} \
		--build-arg ENGINE_VERSION=${TEST_ENGINE_VERSION} \
		--build-arg API_VERSION=${TEST_API_VERSION} \
		--build-arg APT_MIRROR .

.PHONY: build
build:
	docker build \
		--pull \
		-t docker-sdk-python3 \
		-f tests/Dockerfile \
		--build-arg VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER} \
		--build-arg APT_MIRROR .

.PHONY: build-docs
build-docs:
	docker build \
		-t docker-sdk-python-docs \
		-f Dockerfile-docs \
		--build-arg VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER} \
		$(uid_args) \
		.

.PHONY: build-dind-certs
build-dind-certs:
	docker build \
		-t dpy-dind-certs \
		-f tests/Dockerfile-dind-certs \
		--build-arg VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER} \
		.

.PHONY: test
test: ruff unit-test integration-dind integration-dind-ssl

.PHONY: unit-test
unit-test: build
	docker run -t --rm docker-sdk-python3 py.test tests/unit

.PHONY: integration-test
integration-test: build
	docker run -t --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 py.test -v tests/integration/${file}

.PHONY: setup-network
setup-network:
	docker network inspect dpy-tests || docker network create dpy-tests

.PHONY: integration-dind
integration-dind: integration-dind

.PHONY: integration-dind
integration-dind: build setup-network
	docker rm -vf dpy-dind || :

	docker run \
		--detach \
		--name dpy-dind \
		--network dpy-tests \
		--pull=always \
		--privileged \
		docker:${TEST_ENGINE_VERSION}-dind \
		dockerd -H tcp://0.0.0.0:2375 --experimental

	# Wait for Docker-in-Docker to come to life
	docker run \
		--network dpy-tests \
		--rm \
		--tty \
		busybox \
		sh -c 'while ! nc -z dpy-dind 2375; do sleep 1; done'

	docker run \
		--env="DOCKER_HOST=tcp://dpy-dind:2375" \
		--env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}" \
		--network dpy-tests \
		--rm \
		--tty \
		docker-sdk-python3 \
		py.test tests/integration/${file}

	docker rm -vf dpy-dind


.PHONY: integration-dind-ssh
integration-dind-ssh: build-dind-ssh build setup-network
	docker rm -vf dpy-dind-ssh || :
	docker run -d --network dpy-tests --name dpy-dind-ssh --privileged \
		docker-dind-ssh dockerd --experimental
	# start SSH daemon for known key
	docker exec dpy-dind-ssh sh -c "/usr/sbin/sshd -h /etc/ssh/known_ed25519 -p 22"
	docker exec dpy-dind-ssh sh -c "/usr/sbin/sshd -h /etc/ssh/unknown_ed25519 -p 2222"
	docker run \
		--tty \
		--rm \
		--env="DOCKER_HOST=ssh://dpy-dind-ssh" \
		--env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}" \
		--env="UNKNOWN_DOCKER_SSH_HOST=ssh://dpy-dind-ssh:2222" \
		--network dpy-tests \
		docker-sdk-python3 py.test tests/ssh/${file}
	docker rm -vf dpy-dind-ssh


.PHONY: integration-dind-ssl
integration-dind-ssl: build-dind-certs build setup-network
	docker rm -vf dpy-dind-certs dpy-dind-ssl || :
	docker run -d --name dpy-dind-certs dpy-dind-certs

	docker run \
		--detach \
		--env="DOCKER_CERT_PATH=/certs" \
		--env="DOCKER_HOST=tcp://localhost:2375" \
		--env="DOCKER_TLS_VERIFY=1" \
		--name dpy-dind-ssl \
		--network dpy-tests \
		--network-alias docker \
		--pull=always \
		--privileged \
		--volume /tmp \
		--volumes-from dpy-dind-certs \
		docker:${TEST_ENGINE_VERSION}-dind \
		dockerd \
			--tlsverify \
			--tlscacert=/certs/ca.pem \
			--tlscert=/certs/server-cert.pem \
			--tlskey=/certs/server-key.pem \
			-H tcp://0.0.0.0:2375 \
			--experimental

	# Wait for Docker-in-Docker to come to life
	docker run \
		--network dpy-tests \
		--rm \
		--tty \
		busybox \
		sh -c 'while ! nc -z dpy-dind-ssl 2375; do sleep 1; done'

	docker run \
		--env="DOCKER_CERT_PATH=/certs" \
		--env="DOCKER_HOST=tcp://docker:2375" \
		--env="DOCKER_TEST_API_VERSION=${TEST_API_VERSION}" \
		--env="DOCKER_TLS_VERIFY=1" \
		--network dpy-tests \
		--rm \
		--volumes-from dpy-dind-ssl \
		--tty \
		docker-sdk-python3 \
		py.test tests/integration/${file}

	docker rm -vf dpy-dind-ssl dpy-dind-certs

.PHONY: ruff
ruff: build
	docker run -t --rm docker-sdk-python3 ruff docker tests

.PHONY: docs
docs: build-docs
	docker run --rm -t -v `pwd`:/src docker-sdk-python-docs sphinx-build docs docs/_build

.PHONY: shell
shell: build
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 python
