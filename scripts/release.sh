#!/bin/bash
#
# Create the official release
#

VERSION=$1
REPO=docker/docker-py
GITHUB_REPO=git@github.com:$REPO

if [ -z $VERSION ]; then
    echo "Usage: $0 VERSION [upload]"
    exit 1
fi

echo "##> Removing stale build files and other untracked files"
git clean -x -d -i
test -z "$(git clean -x -d -n)" || exit 1

echo "##> Tagging the release as $VERSION"
git tag $VERSION
if [[ $? != 0 ]]; then
    head_commit=$(git show --pretty=format:%H HEAD)
    tag_commit=$(git show --pretty=format:%H $VERSION)
    if [[ $head_commit != $tag_commit ]]; then
        echo "ERROR: tag already exists, but isn't the current HEAD"
        exit 1
    fi
fi
if  [[ $2 == 'upload' ]]; then
    echo "##> Pushing tag to github"
    git push $GITHUB_REPO $VERSION || exit 1
fi


echo "##> sdist & wheel"
python setup.py sdist bdist_wheel

if [[ $2 == 'upload' ]]; then
    echo '##> Uploading sdist to pypi'
    twine upload dist/docker-$VERSION*
fi
