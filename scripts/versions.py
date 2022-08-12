import operator
import re
from collections import namedtuple

import requests

base_url = 'https://download.docker.com/linux/static/{0}/x86_64/'
categories = [
    'edge',
    'stable',
    'test'
]

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
        """Return a representation that allows this object to be sorted
        correctly with the default comparator.
        """
        # non-GA releases should appear before GA releases
        # Order: tp -> beta -> rc -> GA
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


def main():
    results = set()
    for url in [base_url.format(cat) for cat in categories]:
        res = requests.get(url)
        content = res.text
        versions = [Version.parse(v) for v in re.findall(
            r'"docker-([0-9]+\.[0-9]+\.[0-9]+-?.*)\.tgz"', content
        )]
        sorted_versions = sorted(
            versions, reverse=True, key=operator.attrgetter('order')
        )
        latest = sorted_versions[0]
        results.add(str(latest))
    print(' '.join(results))

if __name__ == '__main__':
    main()
