#! /bin/bash
cd "$(dirname "$0")"

mkdir -p dags logs plugins credentials temp
chown -R 50000 {dags,logs,plugins,credentials,temp,datasets}

docker-compose up airflow-init
