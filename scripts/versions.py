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


class Version(namedtuple('_Version', 'major minor patch rc edition')):

    @classmethod
    def parse(cls, version):
        edition = None
        version = version.lstrip('v')
        version, _, rc = version.partition('-')
        if rc:
            if 'rc' not in rc:
                edition = rc
                rc = None
            elif '-' in rc:
                edition, rc = rc.split('-')

        major, minor, patch = version.split('.', 3)
        return cls(major, minor, patch, rc, edition)

    @property
    def major_minor(self):
        return self.major, self.minor

    @property
    def order(self):
        """Return a representation that allows this object to be sorted
        correctly with the default comparator.
        """
        # rc releases should appear before official releases
        rc = (0, self.rc) if self.rc else (1, )
        return (int(self.major), int(self.minor), int(self.patch)) + rc

    def __str__(self):
        rc = '-{}'.format(self.rc) if self.rc else ''
        edition = '-{}'.format(self.edition) if self.edition else ''
        return '.'.join(map(str, self[:3])) + edition + rc


def main():
    results = set()
    for url in [base_url.format(cat) for cat in categories]:
        res = requests.get(url)
        content = res.text
        versions = [
            Version.parse(
                v.strip('"').lstrip('docker-').rstrip('.tgz').rstrip('-x86_64')
            ) for v in re.findall(
                r'"docker-[0-9]+\.[0-9]+\.[0-9]+-.*tgz"', content
            )
        ]
        sorted_versions = sorted(
            versions, reverse=True, key=operator.attrgetter('order')
        )
        latest = sorted_versions[0]
        results.add(str(latest))
    print(' '.join(results))

if __name__ == '__main__':
    main()
