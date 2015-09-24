.PHONY: all build test integration-test unit-test build-py3 unit-test-py3 integration-test-py3

all: test

clean:
	docker rm -vf dpy-dind

build:
	docker build -t docker-py .

build-py3:
	docker build -t docker-py3 -f Dockerfile-py3 .

test: flake8 unit-test unit-test-py3 integration-dind

unit-test: build
	docker run docker-py py.test tests/unit

unit-test-py3: build-py3
	docker run docker-py3 py.test tests/unit

integration-test: build
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py py.test -rxs tests/integration

integration-test-py3: build-py3
	docker run -v /var/run/docker.sock:/var/run/docker.sock docker-py3 py.test -rxs tests/integration

integration-dind: build build-py3
	docker run -d --name dpy-dind --privileged dockerswarm/dind:1.8.1 docker -d -H tcp://0.0.0.0:2375
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py py.test -rxs tests/integration
	docker run --env="DOCKER_HOST=tcp://docker:2375" --link=dpy-dind:docker docker-py3 py.test -rxs tests/integration
	docker rm -vf dpy-dind

flake8: build
	docker run docker-py flake8 docker tests
