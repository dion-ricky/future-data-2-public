import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow import configuration
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.bigquery_operator import BigQueryCreateEmptyDatasetOperator

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime(2021, 10, 10),
    'retries': 5,
    'retry_delay': timedelta(minutes=10)
}

with DAG(
    dag_id='create_dataset',
    schedule_interval='@once',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_task'
    )

    create_dataset_warehouse_task = BigQueryCreateEmptyDatasetOperator(
        task_id='create_dataset_warehouse',
        dataset_id='sapporo_warehouse',
        bigquery_conn_id='gcp_conn'
    )

    finish_task = DummyOperator(
        task_id='finish_task'
    )

    start_task >> create_dataset_warehouse_task >> finish_task