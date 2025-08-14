"""Setup script for SEO Bot - Independent Installation."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="seo-bot",
    version="1.0.0",
    author="SEO Bot Team",
    author_email="hello@seobot.ai",
    description="AI-powered SEO automation platform with intelligent keyword research, content clustering, and performance optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/seo-bot",
    project_urls={
        "Bug Tracker": "https://github.com/your-org/seo-bot/issues",
        "Documentation": "https://seobot.ai/docs",
        "Homepage": "https://seobot.ai",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Marketing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "ruff>=0.1.7",
            "mypy>=1.7.1",
            "pre-commit>=3.5.0",
        ],
        "full": [
            "spacy>=3.7.2",
            "playwright>=1.40.0",
            "selenium>=4.15.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "seo-bot=seo_bot.cli:app",
        ],
    },
    keywords=["seo", "keyword-research", "content-optimization", "ai", "marketing", "automation"],
    include_package_data=True,
    zip_safe=False,
)