#!/bin/bash
BASE_PATH=$(cd $(dirname $(dirname "${BASH_SOURCE:-$0}")) && pwd)

# Echo commands
set -x

cd $BASE_PATH
git ls-files | entr -s './scripts/lint.sh && pytest'
