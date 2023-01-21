#!/bin/bash
set -eo pipefail
mkdir -p site/checklists
exec python _generator/build_all.py