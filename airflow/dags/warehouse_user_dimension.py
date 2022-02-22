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
    'start_date': datetime.combine(datetime.today() - timedelta(days=7), datetime.min.time()),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='warehouse_user_dimension',
    schedule_interval='0 2 * * *',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_warehouse_user_dimension'
    )

    sensor_app_store = ExternalTaskSensor(
        task_id='sensor_staging_app_store',
        external_dag_id='staging_reviews_app_store',
        external_task_id='finish_staging_review',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True
    )

    sensor_play_store = ExternalTaskSensor(
        task_id='sensor_staging_play_store',
        external_dag_id='staging_reviews_play_store',
        external_task_id='finish_staging_review',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True
    )

    wait_sensor = DummyOperator(
        task_id='wait_sensor'
    )

    start_task >> sensor_app_store >> wait_sensor
    start_task >> sensor_play_store >> wait_sensor

    sql_user_dimension = """#standardSQL
    WITH mark_latest AS (
        SELECT
            *,
            ROW_NUMBER() OVER(PARTITION BY user_name, user_image ORDER BY dag_execution_date DESC) AS duplicate_id
        FROM
            sapporo_staging.app_review
    ),
    unique_identifier AS (
        SELECT 
            TO_BASE64(SHA512(CONCAT(user_name, user_image))) AS id,
            user_name,
            user_image
        FROM 
            mark_latest
        WHERE
            duplicate_id = 1
    ),
    deduped AS (
        SELECT
            DISTINCT id,
            user_name,
            user_image
        FROM
            unique_identifier
    )
    SELECT
        id,
        user_name,
        user_image
    FROM 
        deduped;
    """

    warehouse_user_dimension = BigQueryOperator(
        task_id='warehouse_user_dimension',
        sql=sql_user_dimension,
        destination_dataset_table='sapporo_warehouse.user_dim',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_warehouse_user_dimension'
    )

    wait_sensor >> warehouse_user_dimension >> finish_task