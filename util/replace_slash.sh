#!/bin/sh
sed -i --follow-symlinks "s|%5C|/|g" "$@"


