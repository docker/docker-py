#!/bin/bash
#
# Create the official release
#

if [ -z "$(command -v pandoc 2> /dev/null)" ]; then
    >&2 echo "$0 requires http://pandoc.org/"
    >&2 echo "Please install it and make sure it is available on your \$PATH."
    exit 2
fi

VERSION=$1
REPO=docker/docker-py
GITHUB_REPO=git@github.com:$REPO

if [ -z $VERSION ]; then
    echo "Usage: $0 VERSION [upload]"
    exit 1
fi

echo "##> Tagging the release as $VERSION"
git tag $VERSION || exit 1
if  [[ $2 == 'upload' ]]; then
    echo "##> Pushing tag to github"
    git push $GITHUB_REPO $VERSION || exit 1
fi


pandoc -f markdown -t rst README.md -o README.rst || exit 1
if [[ $2 == 'upload' ]]; then
    echo "##> Uploading sdist to pypi"
    python setup.py sdist bdist_wheel upload
fi
