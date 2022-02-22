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
    dag_id='staging_app_details_app_store',
    schedule_interval='0 1 * * *',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_staging_app_details'
    )

    sensor_app_details_task = ExternalTaskSensor(
        task_id='sensor_fetch_raw_app_details_app_store',
        external_dag_id='fetch_app_details_app_store',
        external_task_id='finish_fetch_app_details',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True,
        retries=5,
        retry_delay=timedelta(minutes=15)
    )

    start_task >> sensor_app_details_task

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
        WITH unique_identifier AS (
            SELECT 
                TO_BASE64(SHA512(
                ARRAY_TO_STRING(ARRAY_CONCAT(
                    [appId, version],
                    screenshots
                ), ", "))) AS unique_id,
                *
            FROM 
                sapporo.{app}_app_store_app_details
        ),
        mark_duplicate AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY updated DESC) AS duplicate_id
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
            appId AS app_id,
            SAFE_CAST(id AS STRING) AS alt_app_id,
            title AS app_name,
            url,
            version AS version,
            description,
            "App Store" AS platform,
            SAFE_CAST(primaryGenreId AS STRING) AS genre_id,
            primaryGenre AS genre,
            score AS rating,
            reviews AS rating_count,
            reviews AS review_count,
            SAFE_CAST(price AS FLOAT64) AS original_price,
            FALSE AS is_on_sale,
            `free` AS is_free,
            currency,
            SAFE_CAST(size AS FLOAT64) AS size_in_byte,
            requiredOsVersion AS min_os_version,
            released AS released_date,
            updated AS updated_date,
            screenshots,
            releaseNotes AS recent_changes,
            developer,
            SAFE_CAST(developerId AS STRING) AS developer_id,
            '' AS developer_email,
            developerWebsite AS developer_website,
            contentRating AS content_rating,
            SAFE_CAST('{execution_date}' AS TIMESTAMP) AS dag_execution_date
        FROM
            deduped
        WHERE
            updated BETWEEN '{start}' AND '{end}';
        """.format(
            app=app['app_name'],
            app_id=app['app_id'],
            start='{{ execution_date.subtract(hours=1) }}',
            end='{{ next_execution_date.subtract(hours=1, seconds=1) }}',
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

        sensor_app_details_task >> staging_app_details_task >> wait_task

    # finish
    finish_task = DummyOperator(
        task_id='finish_staging_app_details'
    )

    wait_task >> finish_task