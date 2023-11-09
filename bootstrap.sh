#!/bin/sh

ENVBASE=$1
shift 1

exec "${ENVBASE}/bin/python" "${ENVBASE}/main.py" $*
