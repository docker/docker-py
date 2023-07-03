import operator
import re
import requests
from collections import namedtuple


BASE_URL = 'https://download.docker.com/linux/static/{0}/x86_64/'
CATEGORIES = ['edge', 'stable', 'test']
STAGES = ['tp', 'beta', 'rc']


class Version(namedtuple('_Version', 'major minor patch stage edition')):
    @classmethod
    def parse(cls, version):
        edition = None
        version = version.lstrip('v')
        version, _, stage = version.partition('-')
        if stage:
            if not any(marker in stage for marker in STAGES):
                edition = stage
                stage = None
            elif '-' in stage:
                edition, stage = stage.split('-', 1)
        major, minor, patch = version.split('.', 2)
        return cls(major, minor, patch, stage, edition)

    @property
    def major_minor(self):
        return self.major, self.minor

    @property
    def order(self):
        if self.stage:
            for st in STAGES:
                if st in self.stage:
                    stage = (STAGES.index(st), self.stage)
                    break
        else:
            stage = (len(STAGES),)
        return (int(self.major), int(self.minor), int(self.patch)) + stage

    def __str__(self):
        stage = f'-{self.stage}' if self.stage else ''
        edition = f'-{self.edition}' if self.edition else ''
        return '.'.join(map(str, self[:3])) + edition + stage

#encapsulation 
def get_latest_docker_versions():
    results = set()
    session = requests.Session()
    #added exception handling
    try:
        for category in CATEGORIES:
            url = BASE_URL.format(category)
            res = session.get(url)
            res.raise_for_status()
            content = res.text
            versions = [Version.parse(v) for v in re.findall(r'"docker-([0-9]+\.[0-9]+\.[0-9]+-?.*)\.tgz"', content)]
            sorted_versions = sorted(versions, reverse=True, key=operator.attrgetter('order'))
            latest = sorted_versions[0]
            results.add(str(latest))

    except requests.RequestException as e:
        print(f"An error occurred during the request: {e}")

    return results


def main():
    latest_versions = get_latest_docker_versions()
    print(' '.join(latest_versions))


if __name__ == '__main__':
    main()
