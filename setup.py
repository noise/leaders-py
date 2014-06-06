# http://docs.activestate.com/activepython/3.2/diveintopython3/html/packaging.html
from distutils.core import setup

setup(
    name = "leaders",
    packages = ["leaders"],
    version = "0.0.1",
    description = "Leaderboard service, backed by Redis",
    author = "Bret Barker",
    author_email = "bret@abitrandom.net",
    url = "http://abitrandom.net/",
    download_url = "http://github.com/noise/leaders-py",
    keywords = ["game", "leaderboard", "highscore", "redis"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
        "Topic :: Games/Entertainment"
    ],
    long_description = """\
Flexible leaderboard service for use in online/mobile games, backed by Redis.
""",
    install_requires=[
        "redis"
    ]
)
