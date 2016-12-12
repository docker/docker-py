.PHONY: all
all: test

.PHONY: clean
clean:
	-docker rm -vf dpy-dind
	find -name "__pycache__" | xargs rm -rf

.PHONY: build
build:
	docker build -t docker-sdk-python .

.PHONY: build-py3
build-py3:
	docker build -t docker-sdk-python3 -f Dockerfile-py3 .

.PHONY: build-docs
build-docs:
	docker build -t docker-sdk-python-docs -f Dockerfile-docs .

.PHONY: build-dind-certs
build-dind-certs:
	docker build -t dpy-dind-certs -f tests/Dockerfile-dind-certs .

.PHONY: test
test: flake8 unit-test unit-test-py3 integration-dind integration-dind-ssl

.PHONY: unit-test
unit-test: build
	docker run --rm docker-sdk-python py.test tests/unit

.PHONY: unit-test-py3
unit-test-py3: build-py3
	docker run --rm docker-sdk-python3 py.test tests/unit

.PHONY: integration-test
integration-test: build
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python py.test tests/integration/${file}

.PHONY: integration-test-py3
integration-test-py3: build-py3
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python3 py.test tests/integration/${file}

.PHONY: integration-dind
integration-dind: build build-py3
	docker rm -vf dpy-dind || :
	docker run -d --name dpy-dind --privileged dockerswarm/dind:1.13.0-rc3 docker daemon\
		-H tcp://0.0.0.0:2375
	docker run --rm --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-sdk-python\
		py.test tests/integration
	docker run --rm --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-sdk-python3\
		py.test tests/integration
	docker rm -vf dpy-dind

.PHONY: integration-dind-ssl
integration-dind-ssl: build-dind-certs build build-py3
	docker run -d --name dpy-dind-certs dpy-dind-certs
	docker run -d --env="DOCKER_HOST=tcp://localhost:2375" --env="DOCKER_TLS_VERIFY=1"\
		--env="DOCKER_CERT_PATH=/certs" --volumes-from dpy-dind-certs --name dpy-dind-ssl\
		-v /tmp --privileged dockerswarm/dind:1.13.0-rc3 docker daemon --tlsverify\
		--tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem\
		--tlskey=/certs/server-key.pem -H tcp://0.0.0.0:2375
	docker run --rm --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs"\
		--link=dpy-dind-ssl:docker docker-sdk-python py.test tests/integration
	docker run --rm --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs"\
		--link=dpy-dind-ssl:docker docker-sdk-python3 py.test tests/integration
	docker rm -vf dpy-dind-ssl dpy-dind-certs

.PHONY: flake8
flake8: build
	docker run --rm docker-sdk-python flake8 docker tests

.PHONY: docs
docs: build-docs
	docker run --rm -it -v `pwd`:/code docker-sdk-python-docs sphinx-build docs ./_build

.PHONY: shell
shell: build
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock docker-sdk-python python
