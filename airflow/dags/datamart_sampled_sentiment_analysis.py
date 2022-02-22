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
    dag_id='datamart_sampled_sentiment_analysis',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_datamart_sampled_sentiment_analysis'
    )

    sql_sentiment_analysis = """#standardSQL
    WITH t AS (
    SELECT *
    FROM `future-data-track-1.sapporo_mart.sentiment_analysis_dataset`
    ),
    table_stats AS (
    SELECT *, SUM(c) OVER() total 
    FROM (
        SELECT rating, COUNT(*) c 
        FROM t
        GROUP BY 1 
        HAVING c>10000)
    )
    SELECT sample.*
    FROM (
    SELECT ARRAY_AGG(a ORDER BY RAND() LIMIT 66000) cat_samples, rating, ANY_VALUE(c) c
    FROM t a
    JOIN table_stats b
    USING(rating)
    WHERE sentiment != 1 AND review IS NOT NULL
    GROUP BY rating
    ), UNNEST(cat_samples) sample WITH OFFSET off;
    """

    datamart_sampled_sentiment_analysis = BigQueryOperator(
        task_id='datamart_sampled_sentiment_analysis',
        sql=sql_sentiment_analysis,
        destination_dataset_table='sapporo_mart.sampled_sentiment_analysis',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_datamart_sampled_sentiment_analysis'
    )

    start_task >> datamart_sampled_sentiment_analysis >> finish_task