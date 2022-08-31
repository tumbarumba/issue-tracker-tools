#!/bin/bash
BASE_PATH=$(cd $(dirname $(dirname "${BASH_SOURCE:-$0}")) && pwd)

# Echo commands
set -x

# Fail if there are Python syntax errors or undefined names
flake8 $BASE_PATH --count --select=E9,F63,F7,F82 --show-source --statistics
# exit-zero treats all errors as warnings
flake8 $BASE_PATH --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
