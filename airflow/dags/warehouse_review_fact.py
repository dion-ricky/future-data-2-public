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
    dag_id='warehouse_review_fact',
    schedule_interval='0 2 * * *',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_warehouse_review_fact'
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

    sensor_warehouse_app_dimension = ExternalTaskSensor(
        task_id='sensor_warehouse_app_dimension',
        external_dag_id='warehouse_app_dimension',
        external_task_id='finish_warehouse_app_dimension',
        allowed_states=['success'],
        check_existence=True
    )

    sensor_warehouse_review_dimension = ExternalTaskSensor(
        task_id='sensor_warehouse_review_dimension',
        external_dag_id='warehouse_review_dimension',
        external_task_id='finish_warehouse_review_dimension',
        allowed_states=['success'],
        check_existence=True
    )

    sensor_warehouse_user_dimension = ExternalTaskSensor(
        task_id='sensor_warehouse_user_dimension',
        external_dag_id='warehouse_user_dimension',
        external_task_id='finish_warehouse_user_dimension',
        allowed_states=['success'],
        check_existence=True
    )

    wait_sensor = DummyOperator(
        task_id='wait_sensor'
    )

    start_task >> sensor_app_store >> wait_sensor
    start_task >> sensor_play_store >> wait_sensor
    start_task >> sensor_warehouse_app_dimension >> wait_sensor
    start_task >> sensor_warehouse_review_dimension >> wait_sensor
    start_task >> sensor_warehouse_user_dimension >> wait_sensor

    sql_review_fact = """#standardSQL
    WITH mark_duplicate AS (
        SELECT 
            *,
            ROW_NUMBER() OVER(PARTITION BY review_id ORDER BY dag_execution_date DESC) AS duplicate_id
        FROM
            sapporo_staging.app_review
    ),
    deduped AS (
        SELECT
            *
        FROM 
            mark_duplicate
        WHERE duplicate_id = 1
    )
    SELECT
        CASE
            WHEN wa.id IS NULL THEN wa2.id
        ELSE wa.id
        END AS app_key,
        wr.id AS review_key,
        wu.id AS user_key,
        wd.date_key AS review_date_key,
        wt.time_key AS review_time_key,
        sr.rating,
        sr.thumbs_up_count
    FROM
        deduped sr
    LEFT JOIN sapporo_warehouse.app_dim wa ON
        sr.app_id = wa.alt_app_id
        AND sr.app_version = wa.version
        AND sr.platform = wa.platform 
    LEFT JOIN sapporo_warehouse.app_dim wa2 ON
        sr.app_id = wa2.alt_app_id 
        AND wa.id IS NULL
        AND wa2.version = ''
        AND sr.platform = wa2.platform 
    LEFT JOIN sapporo_warehouse.review_dim wr ON
        sr.review_id = wr.review_id
    LEFT JOIN sapporo_warehouse.user_dim wu ON
        sr.user_name = wu.user_name
        AND sr.user_image = wu.user_image 
    LEFT JOIN sapporo_warehouse.date_dim wd ON
        DATE(sr.created_date) = wd.full_date
    LEFT JOIN sapporo_warehouse.time_dim wt ON
        TIME(sr.created_date) = wt.`time`;
    """

    warehouse_review_fact = BigQueryOperator(
        task_id='warehouse_review_fact',
        sql=sql_review_fact,
        destination_dataset_table='sapporo_warehouse.app_reviews',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_warehouse_review_fact'
    )

    wait_sensor >> warehouse_review_fact >> finish_task