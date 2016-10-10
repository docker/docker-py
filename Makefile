.PHONY: all
all: test

.PHONY: clean
clean:
	-docker rm -vf dpy-dind
	find -name "__pycache__" | xargs rm -rf

.PHONY: build
build:
	docker build -t docker-py .

.PHONY: build-py3
build-py3:
	docker build -t docker-py3 -f Dockerfile-py3 .

.PHONY: build-docs
build-docs:
	docker build -t docker-py-docs -f Dockerfile-docs .

.PHONY: build-dind-certs
build-dind-certs:
	docker build -t dpy-dind-certs -f tests/Dockerfile-dind-certs .

.PHONY: test
test: flake8 unit-test unit-test-py3 integration-dind integration-dind-ssl

.PHONY: unit-test
unit-test: build
	docker run docker-py py.test tests/unit

.PHONY: unit-test-py3
unit-test-py3: build-py3
	docker run docker-py3 py.test tests/unit

.PHONY: integration-test
integration-test: build
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py py.test tests/integration/${file}

.PHONY: integration-test-py3
integration-test-py3: build-py3
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py3 py.test tests/integration/${file}

.PHONY: integration-dind
integration-dind: build build-py3
	docker rm -vf dpy-dind || :
	docker run -d --name dpy-dind --privileged dockerswarm/dind:1.12.0 docker daemon\
		-H tcp://0.0.0.0:2375
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py\
		py.test tests/integration
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py3\
		py.test tests/integration
	docker rm -vf dpy-dind

.PHONY: integration-dind-ssl
integration-dind-ssl: build-dind-certs build build-py3
	docker run -d --name dpy-dind-certs dpy-dind-certs
	docker run -d --env="DOCKER_HOST=tcp://localhost:2375" --env="DOCKER_TLS_VERIFY=1"\
		--env="DOCKER_CERT_PATH=/certs" --volumes-from dpy-dind-certs --name dpy-dind-ssl\
		-v /tmp --privileged dockerswarm/dind:1.12.0 docker daemon --tlsverify\
		--tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem\
		--tlskey=/certs/server-key.pem -H tcp://0.0.0.0:2375
	docker run --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs"\
		--link=dpy-dind-ssl:docker docker-py py.test tests/integration
	docker run --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375"\
		--env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs"\
		--link=dpy-dind-ssl:docker docker-py3 py.test tests/integration
	docker rm -vf dpy-dind-ssl dpy-dind-certs

.PHONY: flake8
flake8: build
	docker run docker-py flake8 docker tests

.PHONY: docs
docs: build-docs
	docker run -v `pwd`/docs:/home/docker-py/docs/ -p 8000:8000 docker-py-docs mkdocs serve -a 0.0.0.0:8000

.PHONY: shell
shell: build
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock docker-py python
