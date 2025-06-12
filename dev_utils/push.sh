#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: $0 <branch-name>"
  exit 1
fi
if [ -z "$2" ]; then
  echo "Usage: $0 <branch-name> <commit-message>"
  exit 1
fi
cd ../
git add .
git commit -m "$2"
git push origin $1