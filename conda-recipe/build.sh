#!/bin/bash

$PYTHON -m pip install . -vv

mkdir -p $PREFIX/bin/db
cp $RECIPE_DIR/../el_gato/db/* $PREFIX/bin/db/

