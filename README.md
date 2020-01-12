# Kernel Profiling

## Setup

Download ChromeDriver [here](https://chromedriver.chromium.org).

## How to run

```
# clone the repo
git clone https://github.com/harupy/kernel-profiling
cd kernel-profiling

# install pipenv (optional)
pip install pipenv

# install dependencies
pipenv install

# activate the pipenv shell
pipenv shell

# run the script
python profile_kernels.py -c titanic
```
