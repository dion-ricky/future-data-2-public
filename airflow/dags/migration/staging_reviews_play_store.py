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
    'start_date': datetime(2021, 4, 4),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='migrate_staging_reviews_play_store',
    schedule_interval='@once',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_staging_review'
    )

    wait_task = DummyOperator(
        task_id='wait_staging_review'
    )

    apps = [
        {
            'app_name': 'blibli',
            'app_id': 'blibli.mobile.commerce'
        },
        {
            'app_name': 'tokopedia',
            'app_id': 'com.tokopedia.tkpd'
        },
        {
            'app_name': 'shopee',
            'app_id': 'com.shopee.id'
        },
        {
            'app_name': 'bukalapak',
            'app_id': 'com.bukalapak.android'
        },
        {
            'app_name': 'lazada',
            'app_id': 'com.lazada.android'
        },
        {
            'app_name': 'jdid',
            'app_id': 'jd.cdyjy.overseas.market.indonesia'
        },
        {
            'app_name': 'zalora',
            'app_id': 'com.zalora.android'
        },
        {
            'app_name': 'bhinneka',
            'app_id': 'bmd.android.apps'
        },
        {
            'app_name': 'elevenia',
            'app_id': 'id.co.elevenia'
        }
    ]

    for app in apps:
        # In case of sql change
        # modify everything below until WHERE clause
        sql = """#standardSQL
        WITH mark_latest AS (
        SELECT
            reviewId,
            userName,
            userImage ,
            content ,
            score ,
            thumbsUpCount ,
            reviewCreatedVersion ,
            `at` ,
            replyContent ,
            repliedAt,
            ROW_NUMBER() OVER(PARTITION BY reviewId ORDER BY dag_execution_date DESC) AS duplicate_id
        FROM
            sapporo.{app}_play_store_reviews
        ),
        deduped AS (
        SELECT
            reviewId,
            userName,
            userImage,
            content,
            score,
            thumbsUpCount,
            reviewCreatedVersion,
            `at`,
            replyContent,
            repliedAt
        FROM
            mark_latest
        WHERE
            duplicate_id = 1 )
        SELECT
            '{app}' AS app_name,
            '{app_id}' AS app_id,
            reviewId AS review_id,
            userName AS user_name,
            userImage AS user_image,
            content AS review,
            score AS rating,
            thumbsUpCount AS thumbs_up_count,
            reviewCreatedVersion AS app_version,
            `at` AS created_date,
            COALESCE(replyContent, '') AS reply,
            COALESCE(repliedAt, TIMESTAMP('1970-01-01 00:00:00')) AS replied_at,
            'Play Store' AS platform,
            TIMESTAMP('{execution_date}') AS dag_execution_date
        FROM
            deduped
        WHERE
            `at` < '{start}';
        """.format(
            app=app['app_name'],
            app_id=app['app_id'],
            start='{{ execution_date.subtract(days=7) }}',
            execution_date='{{ execution_date }}')

        staging_play_store_task = BigQueryOperator(
            task_id='staging_{}_play_store'.format(app['app_name']),
            sql=sql,
            destination_dataset_table='sapporo_staging.app_review',
            write_disposition='WRITE_APPEND',
            allow_large_results=True,
            bigquery_conn_id='gcp_conn',
            use_legacy_sql=False
        )

        start_task >> staging_play_store_task >> wait_task

    # finish
    finish_task = DummyOperator(
        task_id='finish_staging_review'
    )

    wait_task >> finish_task