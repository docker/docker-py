#!groovy

def imageNameBase = "dockerpinata/docker-py"
def imageNamePy3
def imageDindSSH
def images = [:]

def buildImage = { name, buildargs, pyTag ->
  img = docker.image(name)
  try {
    img.pull()
  } catch (Exception exc) {
    img = docker.build(name, buildargs)
    img.push()
  }
  if (pyTag?.trim()) images[pyTag] = img.id
}

def buildImages = { ->
  wrappedNode(label: "amd64 && ubuntu-2004 && overlay2", cleanWorkspace: true) {
    stage("build image") {
      checkout(scm)

      imageNamePy3 = "${imageNameBase}:py3-${gitCommit()}"
      imageDindSSH = "${imageNameBase}:sshdind-${gitCommit()}"
      withDockerRegistry(credentialsId:'dockerbuildbot-index.docker.io') {
        buildImage(imageDindSSH, "-f tests/Dockerfile-ssh-dind .", "")
        buildImage(imageNamePy3, "-f tests/Dockerfile --build-arg PYTHON_VERSION=3.10 .", "py3.10")
      }
    }
  }
}

def getDockerVersions = { ->
  def dockerVersions = ["19.03.12"]
  wrappedNode(label: "amd64 && ubuntu-2004 && overlay2") {
    def result = sh(script: """docker run --rm \\
        --entrypoint=python \\
        ${imageNamePy3} \\
        /src/scripts/versions.py
      """, returnStdout: true
    )
    dockerVersions = dockerVersions + result.trim().tokenize(' ')
  }
  return dockerVersions
}

def getAPIVersion = { engineVersion ->
  def versionMap = [
    '18.09': '1.39',
    '19.03': '1.40'
  ]
  def result = versionMap[engineVersion.substring(0, 5)]
  if (!result) {
    return '1.40'
  }
  return result
}

def runTests = { Map settings ->
  def dockerVersion = settings.get("dockerVersion", null)
  def pythonVersion = settings.get("pythonVersion", null)
  def testImage = settings.get("testImage", null)
  def apiVersion = getAPIVersion(dockerVersion)

  if (!testImage) {
    throw new Exception("Need test image object, e.g.: `runTests(testImage: img)`")
  }
  if (!dockerVersion) {
    throw new Exception("Need Docker version to test, e.g.: `runTests(dockerVersion: '19.03.12')`")
  }
  if (!pythonVersion) {
    throw new Exception("Need Python version being tested, e.g.: `runTests(pythonVersion: 'py3.x')`")
  }

  { ->
    wrappedNode(label: "amd64 && ubuntu-2004 && overlay2", cleanWorkspace: true) {
      stage("test python=${pythonVersion} / docker=${dockerVersion}") {
        checkout(scm)
        def dindContainerName = "dpy-dind-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        def testContainerName = "dpy-tests-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        def testNetwork = "dpy-testnet-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        withDockerRegistry(credentialsId:'dockerbuildbot-index.docker.io') {
          try {
            // unit tests
            sh """docker run --rm \\
              -e 'DOCKER_TEST_API_VERSION=${apiVersion}' \\
              ${testImage} \\
              py.test -v -rxs --cov=docker tests/unit
            """
            // integration tests
            sh """docker network create ${testNetwork}"""
            sh """docker run --rm -d --name ${dindContainerName} -v /tmp --privileged --network ${testNetwork} \\
              ${imageDindSSH} dockerd -H tcp://0.0.0.0:2375
            """
            sh """docker run --rm \\
              --name ${testContainerName} \\
              -e "DOCKER_HOST=tcp://${dindContainerName}:2375" \\
              -e 'DOCKER_TEST_API_VERSION=${apiVersion}' \\
              --network ${testNetwork} \\
              --volumes-from ${dindContainerName} \\
              -v $DOCKER_CONFIG/config.json:/root/.docker/config.json \\
              ${testImage} \\
              py.test -v -rxs --cov=docker tests/integration
            """
            sh """docker stop ${dindContainerName}"""
            // start DIND container with SSH
            sh """docker run --rm -d --name ${dindContainerName} -v /tmp --privileged --network ${testNetwork} \\
              ${imageDindSSH} dockerd --experimental"""
            sh """docker exec ${dindContainerName} sh -c /usr/sbin/sshd """
            // run SSH tests only
            sh """docker run --rm \\
              --name ${testContainerName} \\
              -e "DOCKER_HOST=ssh://${dindContainerName}:22" \\
              -e 'DOCKER_TEST_API_VERSION=${apiVersion}' \\
              --network ${testNetwork} \\
              --volumes-from ${dindContainerName} \\
              -v $DOCKER_CONFIG/config.json:/root/.docker/config.json \\
              ${testImage} \\
              py.test -v -rxs --cov=docker tests/ssh
            """
          } finally {
            sh """
              docker stop ${dindContainerName}
              docker network rm ${testNetwork}
            """
          }
        }
      }
    }
  }
}


buildImages()

def dockerVersions = getDockerVersions()

def testMatrix = [failFast: false]

for (imgKey in new ArrayList(images.keySet())) {
  for (version in dockerVersions) {
    testMatrix["${imgKey}_${version}"] = runTests([testImage: images[imgKey], dockerVersion: version, pythonVersion: imgKey])
  }
}

parallel(testMatrix)
