#!groovy

def imageNameBase = "dockerbuildbot/docker-py"
def imageNamePy2
def imageNamePy3
def images = [:]

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

      buildImage(imageNamePy2, "-f tests/Dockerfile --build-arg PYTHON_VERSION=2.7 .", "py2.7")
      buildImage(imageNamePy3, "-f tests/Dockerfile --build-arg PYTHON_VERSION=3.7 .", "py3.7")
    }
  }
}

def getDockerVersions = { ->
  def dockerVersions = ["19.03.5"]
  wrappedNode(label: "ubuntu && !zfs && amd64") {
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
            docker:${dockerVersion}-dind dockerd -H tcp://0.0.0.0:2375
          """
          sh """docker run \\
            --name ${testContainerName} \\
            -e "DOCKER_HOST=tcp://${dindContainerName}:2375" \\
            -e 'DOCKER_TEST_API_VERSION=${apiVersion}' \\
            --network ${testNetwork} \\
            --volumes-from ${dindContainerName} \\
            ${testImage} \\
            py.test -v -rxs --cov=docker tests/
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

def dockerVersions = getDockerVersions()

def testMatrix = [failFast: false]

for (imgKey in new ArrayList(images.keySet())) {
  for (version in dockerVersions) {
    testMatrix["${imgKey}_${version}"] = runTests([testImage: images[imgKey], dockerVersion: version, pythonVersion: imgKey])
  }
}

parallel(testMatrix)
