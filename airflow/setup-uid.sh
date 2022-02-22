#! /bin/bash
cd "$(dirname "$0")"

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" >> .env
