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
	dag_id='datamart_2021_app_reviews',
	schedule_interval='@once',
	default_args=default_args) as dag:

	start_task = DummyOperator(
		task_id='start_datamart_2021_app_reviews'
	)

	sql_app_reviews = """#standardSQL
	SELECT 
        wap.app_name,
        wap.app_id,
        wap.alt_app_id,
        wr.review_id,
        wu.user_name,
        wu.user_image,
        wr.review,
        wa.rating,
        wa.thumbs_up_count,
        wap.version AS app_version,
        TIMESTAMP(DATETIME(wd.`year`, wd.`month`, wd.`date`, wt.`hour`, wt.`minute`, wt.`second`), "UTC") AS created_date,
        wr.reply,
        wr.replied_at,
        wr.platform
    FROM 
        sapporo_warehouse.app_reviews wa
    LEFT JOIN sapporo_warehouse.review_dim wr ON
        wa.review_key = wr.id
    LEFT JOIN sapporo_warehouse.app_dim wap ON
        wa.app_key = wap.id
    LEFT JOIN sapporo_warehouse.user_dim wu ON
        wa.user_key = wu.id
    LEFT JOIN sapporo_warehouse.date_dim wd ON
        wa.review_date_key = wd.date_key 
    LEFT JOIN sapporo_warehouse.time_dim wt ON
        wa.review_time_key = wt.time_key
    WHERE wd.full_date BETWEEN '2021-01-01' AND '2021-12-31';
	"""

	load_app_reviews = BigQueryOperator(
        task_id='load_app_reviews',
        sql=sql_app_reviews,
        destination_dataset_table='sapporo_mart.2021_app_reviews',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

	finish_task = DummyOperator(
		task_id='finish_datamart_2021_app_reviews'
	)

	start_task >> load_app_reviews >> finish_task