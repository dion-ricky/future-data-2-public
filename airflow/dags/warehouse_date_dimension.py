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
    dag_id='warehouse_date_dimension',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_warehouse_date_dimension'
    )

    sensor_date_dimension = ExternalTaskSensor(
        task_id='sensor_date_dimension',
        external_dag_id='date_dimension',
        external_task_id='finish',
        allowed_states=['success'],
        check_existence=True,
        retries=5,
        retry_delta=timedelta(minutes=15)
    )

    sql_date_dimension = """#standardSQL
    SELECT
        date_key,
        full_date,
        day_of_week,
        `date`,
        day_name,
        day_abbrev,
        weekday_flag,
        week_num_in_year,
        `month`,
        month_name,
        month_abbrev,
        `quarter`,
        `year`,
        yearmo
    FROM
        sapporo_staging.date_dim;
    """

    warehouse_date_dimension = BigQueryOperator(
        task_id='warehouse_date_dimension',
        sql=sql_date_dimension,
        destination_dataset_table='sapporo_warehouse.date_dim',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_warehouse_date_dimension'
    )

    start_task >> sensor_date_dimension >> \
        warehouse_date_dimension >> finish_task