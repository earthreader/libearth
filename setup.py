try:
    from setuptools import find_packages, setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import find_packages, setup

from libearth.version import VERSION


setup(
    name='libearth',
    version=VERSION,
    description='The core implementation of Earth Reader',
    long_description=None,
    url='http://dahlia.kr/',
    author='Hong Minhee',
    author_email='minhee' '@' 'dahlia.kr',
    license='MIT License',
    packages=find_packages(exclude=['tests'])
)
