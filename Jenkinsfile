#!groovy

def imageNameBase = "dockerbuildbot/docker-py"
def imageNamePy2
def imageNamePy3
def images = [:]

def dockerVersions = [
  "17.06.2-ce",  // Latest EE
  "17.12.1-ce",  // Latest CE stable
  "18.02.0-ce",  // Latest CE edge
  "18.03.0-ce-rc4" // Latest CE RC
]

def buildImage = { name, buildargs, pyTag ->
  img = docker.image(name)
  try {
    img.pull()
  } catch (Exception exc) {
    img = docker.build(name, buildargs)
    img.push()
  }
  images[pyTag] = img.id
}

def buildImages = { ->
  wrappedNode(label: "ubuntu && !zfs && amd64", cleanWorkspace: true) {
    stage("build image") {
      checkout(scm)

      imageNamePy2 = "${imageNameBase}:py2-${gitCommit()}"
      imageNamePy3 = "${imageNameBase}:py3-${gitCommit()}"

      buildImage(imageNamePy2, ".", "py2.7")
      buildImage(imageNamePy3, "-f Dockerfile-py3 .", "py3.6")
    }
  }
}

def getAPIVersion = { engineVersion ->
  def versionMap = ['17.06': '1.30', '17.12': '1.35', '18.02': '1.36', '18.03': '1.37']
  return versionMap[engineVersion.substring(0, 5)]
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
    throw new Exception("Need Docker version to test, e.g.: `runTests(dockerVersion: '1.12.3')`")
  }
  if (!pythonVersion) {
    throw new Exception("Need Python version being tested, e.g.: `runTests(pythonVersion: 'py2.7')`")
  }

  { ->
    wrappedNode(label: "ubuntu && !zfs && amd64", cleanWorkspace: true) {
      stage("test python=${pythonVersion} / docker=${dockerVersion}") {
        checkout(scm)
        def dindContainerName = "dpy-dind-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        def testContainerName = "dpy-tests-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        def testNetwork = "dpy-testnet-\$BUILD_NUMBER-\$EXECUTOR_NUMBER-${pythonVersion}-${dockerVersion}"
        try {
          sh """docker network create ${testNetwork}"""
          sh """docker run -d --name  ${dindContainerName} -v /tmp --privileged --network ${testNetwork} \\
            dockerswarm/dind:${dockerVersion} dockerd -H tcp://0.0.0.0:2375
          """
          sh """docker run \\
            --name ${testContainerName} \\
            -e "DOCKER_HOST=tcp://${dindContainerName}:2375" \\
            -e 'DOCKER_TEST_API_VERSION=${apiVersion}' \\
            --network ${testNetwork} \\
            --volumes-from ${dindContainerName} \\
            ${testImage} \\
            py.test -v -rxs tests/integration
          """
        } finally {
          sh """
            docker stop ${dindContainerName} ${testContainerName}
            docker rm -vf ${dindContainerName} ${testContainerName}
            docker network rm ${testNetwork}
          """
        }
      }
    }
  }
}


buildImages()

def testMatrix = [failFast: false]

for (imgKey in new ArrayList(images.keySet())) {
  for (version in dockerVersions) {
    testMatrix["${imgKey}_${version}"] = runTests([testImage: images[imgKey], dockerVersion: version, pythonVersion: imgKey])
  }
}

parallel(testMatrix)
