#!/usr/bin/env python3
"""
Setup script for QuranBot
Professional 24/7 Quran streaming Discord bot
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
    name="quranbot",
    version="2.1.0",
    author="QuranBot Team",
    author_email="contact@quranbot.com",
    description="Professional 24/7 Quran streaming Discord bot",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/quranbot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Religion",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Religion",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "quranbot=bot.quran_bot:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "*.txt"],
    },
    keywords="discord bot quran islam muslim audio streaming",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/quranbot/issues",
        "Source": "https://github.com/yourusername/quranbot",
        "Documentation": "https://quranbot.readthedocs.io/",
    },
) 