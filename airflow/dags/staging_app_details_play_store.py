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
    dag_id='staging_app_details_play_store',
    schedule_interval='0 1 * * *',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_staging_app_details'
    )

    sensor_app_details_task = ExternalTaskSensor(
        task_id='sensor_fetch_raw_app_details_play_store',
        external_dag_id='fetch_app_details_play_store',
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

        sql = """#standardSQL
            CREATE TEMP FUNCTION
                parse_indonesia_3_huruf_date(d STRING)
                RETURNS TIMESTAMP
                LANGUAGE js AS \"\"\"
                abbr_date = [
                    'Jan',
                    'Feb',
                    'Mar',
                    'Apr',
                    'Mei',
                    'Jun',
                    'Jul',
                    'Agu',
                    'Sep',
                    'Okt',
                    'Nov',
                    'Des'
                ]

                let day, month, year
                [day, month, year] = d.split(' ')

                day = parseInt(day)
                month = abbr_date.indexOf(month)
                year = parseInt(year)

                return new Date(year, month, day, 0, 0, 0, 0)
            \"\"\";
            WITH filter_date AS (
            SELECT
                TO_BASE64(SHA512(
                ARRAY_TO_STRING(ARRAY_CONCAT(
                    [appId, version]
                ), ", "))) AS unique_id,
                *
            FROM
                sapporo.{app}_play_store_app_details
            ),
            mark_duplicate AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY dag_execution_date DESC) AS duplicate_id
            FROM 
                filter_date
            ),
            deduped AS (
            SELECT
                *
            FROM
                mark_duplicate
            WHERE
                duplicate_id = 1
            )
            SELECT
                appId AS app_id,
                '{app_id}' AS alt_app_id,
                title AS app_name,
                url,
                CASE version
                    WHEN 'Bervariasi berdasarkan perangkat' THEN NULL
                    ELSE version
                END AS version,
                description,
                "Play Store" AS platform,
                genreId AS genre_id,
                genre,
                score AS rating,
                ratings AS rating_count,
                reviews AS review_count,
                SAFE_CAST(originalPrice AS FLOAT64) AS original_price,
                sale AS is_on_sale,
                `free` AS is_free,
                currency,
                SAFE_CAST(REGEXP_REPLACE(`size`, "(\\\\d+),*(\\\\d*)M", "\\\\1.\\\\2") AS FLOAT64) * 1000000 AS size_in_byte,
                CASE androidVersion
                    WHEN 'Bervariasi' THEN NULL
                    ELSE androidVersion
                END
                AS min_os_version,
                parse_indonesia_3_huruf_date(released) AS released_date,
                updated AS updated_date,
                screenshots,
                recentChanges AS recent_changes,
                developer,
                developerInternalID AS developer_id,
                developerEmail AS developer_email,
                developerWebsite AS developer_website,
                RIGHT(contentRating, 2) AS content_rating,
                SAFE_CAST('{execution_date}' AS TIMESTAMP) AS dag_execution_date
            FROM
                deduped
            WHERE
                updated BETWEEN '{start}' AND '{end}'
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