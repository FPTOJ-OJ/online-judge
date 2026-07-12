#!/bin/bash
set -e

# Change directory to the workspace root
cd "$(dirname "$0")"

echo "==> Compiling SASS stylesheets..."
./make_style.sh

echo "==> Collecting static assets..."
./dmojsite/bin/python manage.py collectstatic --noinput

echo "==> Build and static assets collection complete!"
