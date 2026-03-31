"""Setup script for RiskOptimizer backend."""

from setuptools import find_packages, setup

setup(
    name="riskoptimizer",
    version="1.0.0",
    description="RiskOptimizer Backend API",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
        if line.strip() and not line.startswith("#")
    ],
    python_requires=">=3.8",
)
