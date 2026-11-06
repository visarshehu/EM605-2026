#!/usr/bin/env bash
# Example 3: MySQL with a BIND MOUNT.
# -v "$(pwd)/mysql-data:/var/lib/mysql"  ->  a folder on YOUR computer holds the data.
set -e

mkdir -p "$(pwd)/mysql-data"

docker run -d \
  --name mysql-bind \
  -e MYSQL_ROOT_PASSWORD=secret \
  -e MYSQL_DATABASE=demo \
  -v "$(pwd)/mysql-data:/var/lib/mysql" \
  -p 3306:3306 \
  mysql:8

echo "Started 'mysql-bind'. MySQL's files now appear in ./mysql-data (try: ls mysql-data)."
