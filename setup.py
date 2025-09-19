from setuptools import setup, find_packages
from pathlib import Path

# ------------------------------------------------------------------------------
# brainz OS packaging configuration (setup.py)
# - Packages only the Python code under ./backend
# - Exposes console scripts that live under backend/scripts/*
# - Loads dependencies from backend/requirements.txt (with a safe fallback)
# ------------------------------------------------------------------------------

# Load long description from README if available (nice for PyPI & tooling)
readme_path = Path("README.md")
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Robust dependency loading (works even if requirements file is missing in some envs)
req_path = Path("backend/requirements.txt")
if req_path.exists():
    install_requires = req_path.read_text(encoding="utf-8").splitlines()
else:
    # Minimal fallback; keep pins in requirements.txt normally
    install_requires = [
        "fastapi",
        "uvicorn",
        "transformers",
        "sqlalchemy",
        "psycopg2-binary",
        "python-dotenv",
        "pydantic",
    ]

setup(
    # --- Basic package metadata ---
    name="brainz",
    version="1.0.1",
    author="Brainz Dev Team",
    description="brainz OS – autonomous, local-first LLM operating system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    keywords=["llm", "ai", "crypto", "fastapi", "transformers", "os", "agents"],
    url="https://brainz.monster",
    project_urls={
        "Documentation": "https://brainz.gitbook.io/os",
        "Source": "https://github.com/brainzmonster/os",
        "Issues": "https://github.com/brainzmonster/os/issues",
    },

    # --- Python compatibility ---
    python_requires=">=3.10",

    # --- Package discovery ---
    # We only package from the 'backend' directory; e.g. backend/core, backend/models, etc.
    packages=find_packages(where="backend", exclude=("tests", "web", "database")),
    package_dir={"": "backend"},
    include_package_data=True,   # Include non-Python files if declared via MANIFEST.in
    zip_safe=False,              # Some components rely on actual file paths

    # --- Dependencies ---
    install_requires=install_requires,
    extras_require={
        "dev": ["pytest", "black", "ruff", "mypy"],
        "rich": ["rich"],  # pretty console output option
    },

    # --- Console entry points ---
    # IMPORTANT: Ensure these modules exist
    entry_points={
        "console_scripts": [
            "brainz-train=scripts.train_model:main",  # Train command
            "brainz-server=scripts.run_server:main",  # Launch API server
        ],
    },

    # --- Classifiers for PyPI/metadata consumers ---
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Framework :: FastAPI",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
)
