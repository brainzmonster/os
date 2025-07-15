from setuptools import setup, find_packages

# Load all required dependencies from requirements.txt
with open("backend/requirements.txt") as f:
    requirements = f.read().splitlines()

# Configure the Brainz Python package
setup(
    # Basic metadata
    name="brainz",
    version="1.0.0",
    author="Brainz Dev Team",
    description="Brainz OS – Autonomous LLM system",
    license="MIT",
    keywords=["llm", "ai", "crypto", "fastapi", "transformers"],

    # Package discovery
    packages=find_packages(where="backend"),      # Only scan inside /backend
    package_dir={"": "backend"},                  # Root package path is /backend
    include_package_data=True,                    # Include non-Python files (e.g. static, templates)

    # Dependencies
    install_requires=requirements,

    # CLI entry points
    entry_points={
        "console_scripts": [
            "brainz-train=scripts.train_model:main",   # Train command: brainz-train
            "brainz-server=scripts.run_server:main",   # Launch API server: brainz-server
        ],
    },

    # Packaging preferences
    zip_safe=False,  # Not safe to run from zipped .egg (uses file paths internally)
)
