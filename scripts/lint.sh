#!/bin/bash
BASE_PATH=$(cd $(dirname $(dirname "${BASH_SOURCE:-$0}")) && pwd)

# exit when any command fails
set -e
# Echo commands
set -x

# Fail if there are Python syntax errors or undefined names
flake8 --count --select=E9,F63,F7,F82 --show-source --statistics $BASE_PATH/src
# exit-zero treats all errors as warnings
flake8 --count --max-complexity=10 --max-line-length=127 --statistics $BASE_PATH/src
