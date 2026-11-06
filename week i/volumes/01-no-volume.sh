#!/usr/bin/env bash
# Example 1: MySQL with NO volume.
# Data lives in the container's writable layer and is lost when the container is removed.
set -e

docker run -d \
  --name mysql-novol \
  -e MYSQL_ROOT_PASSWORD=secret \
  -e MYSQL_DATABASE=demo \
  -p 3306:3306 \
  mysql:8

echo "Started 'mysql-novol'. Give it ~15s to initialize, then try the commands in README.md."
