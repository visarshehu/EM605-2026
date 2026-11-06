#!/usr/bin/env bash
# Example 2: MySQL with a NAMED VOLUME.
# -v dbdata:/var/lib/mysql  ->  Docker manages the storage; data survives 'docker rm'.
set -e

docker run -d \
  --name mysql-named \
  -e MYSQL_ROOT_PASSWORD=secret \
  -e MYSQL_DATABASE=demo \
  -v dbdata:/var/lib/mysql \
  -p 3306:3306 \
  mysql:8

echo "Started 'mysql-named' backed by the 'dbdata' volume. See README.md to test persistence."
