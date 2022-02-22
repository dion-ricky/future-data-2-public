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
    'start_date': datetime(2021, 12, 31),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='datamart_topic_modelling',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_datamart_topic_modelling'
    )

    sql_topic_modelling = """#standardSQL
    SELECT 
        wr.review_id,
        wr.review,
        wa.rating,
        TIMESTAMP(DATETIME(wd.`year`, wd.`month`, wd.`date`, td.`hour`, td.`minute`, td.`second`), "UTC") AS created_date,
    FROM 
        sapporo_warehouse.app_reviews wa
    LEFT JOIN sapporo_warehouse.review_dim wr ON
        wa.review_key = wr.id
    LEFT JOIN sapporo_warehouse.date_dim wd ON
        wa.review_date_key = wd.date_key
    LEFT JOIN sapporo_warehouse.time_dim td ON
        td.time_key = wa.review_time_key 
    WHERE wd.full_date BETWEEN '2020-11-01' AND '2021-12-01';
    """

    datamart_topic_modelling = BigQueryOperator(
        task_id='datamart_topic_modelling',
        sql=sql_topic_modelling,
        destination_dataset_table='sapporo_mart.topic_modelling',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_datamart_topic_modelling'
    )

    start_task >> datamart_topic_modelling >> finish_task