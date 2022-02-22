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
    dag_id='warehouse_app_info_fact',
    schedule_interval='0 2 * * *',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_warehouse_app_info_fact'
    )

    sensor_app_store = ExternalTaskSensor(
        task_id='sensor_staging_app_store',
        external_dag_id='staging_app_details_app_store',
        external_task_id='finish_staging_app_details',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True
    )

    sensor_play_store = ExternalTaskSensor(
        task_id='sensor_staging_play_store',
        external_dag_id='staging_app_details_play_store',
        external_task_id='finish_staging_app_details',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True
    )

    sensor_warehouse_app_dimension = ExternalTaskSensor(
        task_id='sensor_warehouse_app_dimension',
        external_dag_id='warehouse_app_dimension',
        external_task_id='finish_warehouse_app_dimension',
        allowed_states=['success'],
        check_existence=True
    )

    wait_sensor = DummyOperator(
        task_id='wait_sensor'
    )

    start_task >> sensor_app_store >> wait_sensor
    start_task >> sensor_play_store >> wait_sensor
    start_task >> sensor_warehouse_app_dimension >> wait_sensor

    sql_app_info_fact = """#standardSQL
    WITH unique_identifier AS (
    SELECT 
        TO_BASE64(SHA512(
        ARRAY_TO_STRING(ARRAY_CONCAT(
            [app_id, version]
        ), ", "))) AS id,
        *
    FROM 
        sapporo_staging.app_details
    ),
    mark_duplicate AS (
        SELECT
            *,
            ROW_NUMBER() OVER(PARTITION BY id ORDER BY dag_execution_date DESC) AS duplicate_id
        FROM 
            unique_identifier
    ),
    deduped AS (
        SELECT
            *
        FROM 
            mark_duplicate
        WHERE duplicate_id = 1
    )
    SELECT 
        COALESCE(wa.id, wa2.id) AS app_key,
        sa.original_price,
        sa.rating,
        sa.rating_count,
        sa.review_count,
        sa.size_in_byte,
        wd2.date_key AS updated_date_key,
        wt.time_key AS updated_time_key
    FROM 
        deduped sa
    LEFT JOIN sapporo_warehouse.app_dim wa ON
        sa.alt_app_id = wa.alt_app_id
        AND sa.version = wa.version
        AND sa.platform = wa.platform
    LEFT JOIN sapporo_warehouse.app_dim wa2 ON
        sa.alt_app_id = wa2.alt_app_id
        AND wa.id IS NULL 
        AND wa2.version = ''
        AND sa.platform = wa2.platform 
    LEFT JOIN sapporo_warehouse.date_dim wd2 ON
        DATE(sa.updated_date) = DATE(wd2.full_date)
    LEFT JOIN sapporo_warehouse.time_dim wt ON
        TIME(sa.updated_date) = wt.`time`
    WHERE sa.version <> ''
    """

    warehouse_app_info_fact = BigQueryOperator(
        task_id='warehouse_app_info_fact',
        sql=sql_app_info_fact,
        destination_dataset_table='sapporo_warehouse.app_info',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_warehouse_app_info_fact'
    )

    wait_sensor >> warehouse_app_info_fact >> finish_task