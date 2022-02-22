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

schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/staging/content_review.json')

with DAG(
    dag_id='staging_reviews_app_store',
    schedule_interval='0 1 * * *',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_staging_review'
    )

    sensor_app_store_task = ExternalTaskSensor(
        task_id='sensor_fetch_raw_app_store',
        external_dag_id='fetch_reviews_app_store',
        external_task_id='finish_fetch_reviews',
        allowed_states=['success'],
        execution_delta=timedelta(hours=1),
        check_existence=True,
        retries=5,
        retry_delay=timedelta(minutes=15)
    )

    start_task >> sensor_app_store_task

    wait_task = DummyOperator(
        task_id='wait_staging_review'
    )

    app_store_apps = [
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

    for app in app_store_apps:
        sql = """
        WITH mark_latest AS (
        SELECT
            id,
            userName,
            userUrl,
            version,
            score,
            title,
            text,
            url,
            updated,
            ROW_NUMBER() OVER(PARTITION BY id
        ORDER BY
            updated DESC) AS duplicate_id
        FROM
            sapporo.{app}_app_store_reviews ),
        deduped AS (
        SELECT
            id,
            userName,
            userUrl,
            version,
            score,
            title,
            text,
            url,
            updated
        FROM
            mark_latest
        WHERE
            duplicate_id = 1 )
        SELECT
            '{app}' AS app_name,
            '{app_id}' AS app_id,
            id AS review_id,
            userName AS user_name,
            '' AS user_image,
            CONCAT(title, ', ', text) AS review,
            score AS rating,
            0 AS thumbs_up_count,
            version AS app_version,
            updated AS created_date,
            '' AS reply,
            TIMESTAMP('1970-01-01 00:00:00') AS replied_at,
            'App Store' AS platform,
            TIMESTAMP('{execution_date}') AS dag_execution_date
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

        staging_app_store_task = BigQueryOperator(
            task_id='staging_{}_app_store'.format(app['app_name']),
            sql=sql,
            destination_dataset_table='sapporo_staging.app_review',
            write_disposition='WRITE_APPEND',
            allow_large_results=True,
            bigquery_conn_id='gcp_conn',
            use_legacy_sql=False
        )

        sensor_app_store_task >> staging_app_store_task >> wait_task
    
    # finish
    finish_task = DummyOperator(
        task_id='finish_staging_review'
    )

    wait_task >> finish_task