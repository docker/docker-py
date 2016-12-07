#!groovy

def imageNameBase = "dockerbuildbot/docker-py"
def imageNamePy2
def imageNamePy3
def images = [:]
def dockerVersions = ["1.12.3", "1.13.0-rc3"]

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
      buildImage(imageNamePy3, "-f Dockerfile-py3 .", "py3.5")
    }
  }
}

def runTests = { Map settings ->
  def dockerVersion = settings.get("dockerVersion", null)
  def testImage = settings.get("testImage", null)

  if (!testImage) {
    throw new Exception("Need test image object, e.g.: `runTests(testImage: img)`")
  }
  if (!dockerVersion) {
    throw new Exception("Need Docker version to test, e.g.: `runTests(dockerVersion: '1.12.3')`")
  }

  { ->
    wrappedNode(label: "ubuntu && !zfs && amd64", cleanWorkspace: true) {
      stage("test image=${testImage} / docker=${dockerVersion}") {
        checkout(scm)
        try {
          sh """docker run -d --name dpy-dind-\$BUILD_NUMBER -v /tmp --privileged \\
            dockerswarm/dind:${dockerVersion} docker daemon -H tcp://0.0.0.0:2375
          """
          sh """docker run \\
            --name dpy-tests-\$BUILD_NUMBER --volumes-from dpy-dind-\$BUILD_NUMBER \\
            -e 'DOCKER_HOST=tcp://docker:2375' \\
            --link=dpy-dind-\$BUILD_NUMBER:docker \\
            ${testImage} \\
            py.test -rxs tests/integration
          """
        } finally {
          sh """
            docker stop dpy-tests-\$BUILD_NUMBER dpy-dind-\$BUILD_NUMBER
            docker rm -vf dpy-tests-\$BUILD_NUMBER dpy-dind-\$BUILD_NUMBER
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
    testMatrix["${imgKey}_${version}"] = runTests([testImage: images[imgKey], dockerVersion: version])
  }
}

parallel(testMatrix)
