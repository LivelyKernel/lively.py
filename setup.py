from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
version = "0.1.1"

with open(path.join(here, 'README'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = 'lively',
    version = version,
    description = 'Lively comes to Python',
    author = 'Robert Krahn',
    author_email = 'robert.krahn@gmail.com',
    url = 'https://github.com/rksm/lively.py',
    download_url = 'https://github.com/rksm/lively.py/archive/{}.tar.gz'.format(version),
    keywords = ['lively', "Lively Kernel", 'live programming', 'ide', 'programming tools'],
    long_description=long_description,
    license='MIT',

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Text Editors :: Integrated Development Environments (IDE)',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
    ],

    python_requires='>=3',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
      "yapf",
      "jedi",
      "websockets"
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': [],
        'test': [],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        # 'sample': ['package_data.dat'],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': ['lively.py-server=lively.command_line:main'],
    }
)
