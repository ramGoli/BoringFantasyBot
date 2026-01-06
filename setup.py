"""
Setup script for the Fantasy Football Auto-Lineup Bot.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="fantasy-football-bot",
    version="1.0.0",
    author="Fantasy Football Bot Team",
    author_email="support@fantasyfootballbot.com",
    description="Automated fantasy football lineup management for Yahoo Fantasy Sports",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fantasy-football-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "fantasy-bot=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
    keywords="fantasy football yahoo sports automation lineup optimization",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/fantasy-football-bot/issues",
        "Source": "https://github.com/yourusername/fantasy-football-bot",
        "Documentation": "https://github.com/yourusername/fantasy-football-bot#readme",
    },
)

