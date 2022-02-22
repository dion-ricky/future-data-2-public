import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow import configuration
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

from contrib.utils.dag_output_path import DAGOutputPath

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime(2021, 10, 10),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='warehouse_time_dimension',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_warehouse_time_dimension'
    )

    sensor_time_dimension = ExternalTaskSensor(
        task_id='sensor_time_dimension',
        external_dag_id='time_dimension',
        external_task_id='finish',
        allowed_states=['success'],
        check_existence=True,
        retries=5,
        retry_delta=timedelta(minutes=15)
    )

    sql_time_dimension = """#standardSQL
    SELECT 
        time_key,
        time_id AS time,
        `hour`,
        `minute`,
        `second`,
        meridiem,
        time_of_day
    FROM 
        sapporo_staging.time_dim;
    """

    warehouse_time_dimension = BigQueryOperator(
        task_id='warehouse_time_dimension',
        sql=sql_time_dimension,
        destination_dataset_table='sapporo_warehouse.time_dim',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_warehouse_time_dimension'
    )

    start_task >> sensor_time_dimension >> \
        warehouse_time_dimension >> finish_task