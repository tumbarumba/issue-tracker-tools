#!/bin/bash
BASE_PATH=$(cd $(dirname $(dirname "${BASH_SOURCE:-$0}")) && pwd)

# Echo commands
set -x

$BASE_PATH/scripts/lint.sh
pytest -v
