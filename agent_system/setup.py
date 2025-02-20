import setuptools
import glob

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()
    
setuptools.setup(
    name='mesa_restaurant_agents',
    version='0.0.1',
    author = "",
    author_email = "",
    description = "",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    include_package_data=True,
    python_requires = ">=3.6"
)