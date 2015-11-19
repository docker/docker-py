.PHONY: all build test integration-test unit-test build-py3 unit-test-py3 integration-test-py3

all: test

clean:
	rm -rf tests/__pycache__
	rm -rf tests/*/__pycache__
	docker rm -vf dpy-dind

build:
	docker build -t docker-py .

build-py3:
	docker build -t docker-py3 -f Dockerfile-py3 .

build-dind-certs:
	docker build -t dpy-dind-certs -f tests/Dockerfile-dind-certs .

test: flake8 unit-test unit-test-py3 integration-dind integration-dind-ssl

unit-test: build
	docker run docker-py py.test tests/unit

unit-test-py3: build-py3
	docker run docker-py3 py.test tests/unit

integration-test: build
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py py.test tests/integration

integration-test-py3: build-py3
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py3 py.test tests/integration

integration-dind: build build-py3
	docker run -d --name dpy-dind --env="DOCKER_HOST=tcp://localhost:2375" --privileged dockerswarm/dind:1.9.0 docker -d -H tcp://0.0.0.0:2375
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py py.test tests/integration
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py3 py.test tests/integration
	docker rm -vf dpy-dind

integration-dind-ssl: build-dind-certs build build-py3
	docker run -d --name dpy-dind-certs dpy-dind-certs
	docker run -d --env="DOCKER_HOST=tcp://localhost:2375" --env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --volumes-from dpy-dind-certs --name dpy-dind-ssl -v /tmp --privileged dockerswarm/dind:1.9.0 docker daemon --tlsverify --tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem --tlskey=/certs/server-key.pem -H tcp://0.0.0.0:2375
	docker run --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375" --env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --link=dpy-dind-ssl:docker docker-py py.test tests/integration
	docker run --volumes-from dpy-dind-ssl --env="DOCKER_HOST=tcp://docker:2375" --env="DOCKER_TLS_VERIFY=1" --env="DOCKER_CERT_PATH=/certs" --link=dpy-dind-ssl:docker docker-py3 py.test tests/integration
	docker rm -vf dpy-dind-ssl dpy-dind-certs

flake8: build
	docker run docker-py flake8 docker tests
