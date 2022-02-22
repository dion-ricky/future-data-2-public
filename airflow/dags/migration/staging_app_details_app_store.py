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
    dag_id='migrate_staging_app_details_app_store',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_staging_app_details'
    )

    wait_task = DummyOperator(
        task_id='wait_staging_app_details'
    )

    apps = [
        {
            'app_id': 1034231507,
            'app_name': 'blibli'
        },
        {
            'app_id': 1001394201,
            'app_name': 'tokopedia'
        },
        {
            'app_id': 959841443,
            'app_name': 'shopee'
        },
        {
            'app_id': 1003169137,
            'app_name': 'bukalapak'
        },
        {
            'app_id': 785385147,
            'app_name': 'lazada'
        },
        {
            'app_id': 1060471174,
            'app_name': 'jdid'
        },
        {
            'app_id': 624639017,
            'app_name': 'zalora'
        },
        {
            'app_id': 1446537328,
            'app_name': 'bhinneka'
        },
        {
            'app_id': 827566791,
            'app_name': 'elevenia'
        }
    ]

    for app in apps:
        sql = """#standardSQL
        SELECT
            appId AS app_id,
            '{app_id}' AS alt_app_id,
            '{app}' AS app_name,
            url,
            '' AS version,
            '' AS description,
            "App Store" AS platform,
            SAFE_CAST(primaryGenreId AS STRING) AS genre_id,
            primaryGenre AS genre,
            SAFE_CAST(NULL AS FLOAT64) AS rating,
            SAFE_CAST(NULL AS INT64) AS rating_count,
            SAFE_CAST(NULL AS INT64) AS review_count,
            SAFE_CAST(NULL AS FLOAT64) AS original_price,
            SAFE_CAST(NULL AS BOOLEAN) AS is_on_sale,
            `free` AS is_free,
            currency,
            SAFE_CAST(NULL AS FLOAT64) AS size_in_byte,
            '' AS min_os_version,
            released AS released_date,
            SAFE_CAST('1970-01-01 00:00:00' AS TIMESTAMP) AS updated_date,
            SAFE_CAST(NULL AS ARRAY<STRING>) screenshots,
            '' AS recent_changes,
            developer,
            SAFE_CAST(developerId AS STRING) AS developer_id,
            ''  AS developer_email,
            developerWebsite AS developer_website,
            contentRating AS content_rating,
            SAFE_CAST('{execution_date}' AS TIMESTAMP) AS dag_execution_date
        FROM
            sapporo.{app}_app_store_app_details
        ORDER BY updated DESC
        LIMIT 1;
        """.format(
            app=app['app_name'],
            app_id=app['app_id'],
            execution_date='{{ execution_date }}')

        staging_app_details_task = BigQueryOperator(
            task_id='staging_{}_app_details'.format(app['app_name']),
            sql=sql,
            destination_dataset_table='sapporo_staging.app_details',
            write_disposition='WRITE_APPEND',
            allow_large_results=True,
            bigquery_conn_id='gcp_conn',
            use_legacy_sql=False
        )

        start_task >> staging_app_details_task >> wait_task

    # finish
    finish_task = DummyOperator(
        task_id='finish_staging_app_details'
    )

    wait_task >> finish_task