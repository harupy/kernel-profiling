# Kernel Profiling

A Python script to profile top public kernels on Kaggle.

## Setup

Download ChromeDriver [here](https://chromedriver.chromium.org).

## How to run

```bash
# clone the repo.
git clone https://github.com/harupy/kernel-profiling
cd kernel-profiling

# copy chromedriver
cp /path/to/chromedriver .

# install pipenv (optional).
pip install pipenv

# install dependencies.
pipenv install

# activate the pipenv shell.
pipenv shell

# run the script.
python profile_kernels.py -c titanic

# result will be written to "result.md"
```
