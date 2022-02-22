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
    dag_id='datamart_sentiment_analysis_dataset',
    schedule_interval='0 2 * * *',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_datamart_sentiment_analysis_dataset'
    )

    sensor_warehouse_review = ExternalTaskSensor(
        task_id='sensor_warehouse_review',
        external_dag_id='warehouse_review_fact',
        external_task_id='finish_warehouse_review_fact',
        allowed_states=['success'],
        check_existence=True,
        retries=5,
        retry_delay=timedelta(minutes=15)
    )

    start_task >> sensor_warehouse_review

    sql_sentiment_analysis = """#standardSQL
    SELECT 
        wr.id as review_key,
        wr.review,
        wa.rating,
        CASE
            WHEN wa.rating > 3 THEN 2
            WHEN wa.rating < 3 THEN 0
            ELSE 1
        END AS sentiment
    FROM 
        sapporo_warehouse.app_reviews wa
    LEFT JOIN sapporo_warehouse.review_dim wr ON
        wa.review_key = wr.id
    LEFT JOIN sapporo_warehouse.date_dim wd ON
        wa.review_date_key = wd.date_key;
    """

    datamart_sentiment_analysis_dataset = BigQueryOperator(
        task_id='datamart_sentiment_analysis_dataset',
        sql=sql_sentiment_analysis,
        destination_dataset_table='sapporo_mart.sentiment_analysis_dataset',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_datamart_sentiment_analysis_dataset'
    )

    sensor_warehouse_review >> datamart_sentiment_analysis_dataset >> finish_task