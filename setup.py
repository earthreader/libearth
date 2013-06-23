try:
    from setuptools import find_packages, setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import find_packages, setup
from setuptools.command.test import test

from libearth.version import VERSION


class pytest(test):

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from pytest import main
        errno = main(self.test_args)
        raise SystemExit(errno)


setup(
    name='libearth',
    version=VERSION,
    description='The core implementation of Earth Reader',
    long_description=None,
    url='http://dahlia.kr/',
    author='Hong Minhee',
    author_email='minhee' '@' 'dahlia.kr',
    license='MIT License',
    packages=find_packages(exclude=['tests']),
    tests_require=['pytest >= 2.3.0'],
    cmdclass={'test': pytest}
)
