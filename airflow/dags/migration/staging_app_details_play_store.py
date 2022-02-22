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
    dag_id='migrate_staging_app_details_play_store',
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
        SELECT 
            appId AS app_id,
            '{app_id}' AS alt_app_id,
            '{app}' AS app_name,
            url,
            '' AS version,
            '' AS description,
            "Play Store" AS platform,
            genreId AS genre_id,
            genre,
            SAFE_CAST(NULL AS FLOAT64) AS rating,
            SAFE_CAST(NULL AS INT64) AS rating_count,
            SAFE_CAST(NULL AS INT64) AS review_count,
            SAFE_CAST(NULL AS FLOAT64) AS original_price,
            SAFE_CAST(NULL AS BOOLEAN) AS is_on_sale,
            `free` AS is_free,
            currency,
            '' AS min_os_version,
            parse_indonesia_3_huruf_date(released) AS released_date,
            SAFE_CAST('1970-01-01 00:00:00' AS TIMESTAMP) AS updated_date,
            SAFE_CAST(NULL AS ARRAY<STRING>) AS screenshots,
            '' AS recent_changes,
            developer,
            developerInternalID AS developer_id,
            developerEmail AS developer_email,
            developerWebsite AS developer_website,
            RIGHT(contentRating, 2) AS content_rating,
            SAFE_CAST('{execution_date}' AS TIMESTAMP) AS dag_execution_date
        FROM 
            sapporo.{app}_play_store_app_details
        ORDER BY dag_execution_date DESC
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