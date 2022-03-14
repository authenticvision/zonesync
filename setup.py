from setuptools import setup

setup(
    name='zonesync',
    version='0.0.1',
    packages=['zonesync'],
    install_requires=[
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'zonesync=zonesync.main:main',
        ]
    }
)
