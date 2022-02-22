import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow import configuration
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator

from contrib.utils.dag_output_path import DAGOutputPath
from contrib.operators.play_store_review_operator import PlayStoreReviewOperator

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime.combine(datetime.today() - timedelta(days=7), datetime.min.time()),
    'retries': 5,
    'retry_delay': timedelta(minutes=10)
}

schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/play_store/reviews.json')

with DAG(
    dag_id='fetch_reviews_play_store',
    schedule_interval='@daily',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_fetch_reviews'
    )

    default_params = {
        'lang': 'id',
        'country': 'id',
        'start': '{{ execution_date.int_timestamp }}',
        'end': '{{ next_execution_date.int_timestamp }}',
        'batch_size': 100
    }

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

    review_schema = json.load(open(schema_path))

    wait_task = DummyOperator(
        task_id='wait_task'
    )

    for app in apps:
        params = default_params

        output_path = os.path.join(
                        Variable.get('temp_raw_data'),
                        dag.dag_id,
                        app['app_name'],
                        'reviews_{{ execution_date.format("%Y%m%d") }}.json')
        
        output_path = DAGOutputPath(output_path)

        review_config = {
            'output_path': output_path.path,
            'app_id': app['app_id'],
            'lang': params['lang'],
            'country': params['country'],
            'start': params['start'],
            'end': params['end'],
            'batch_size': params['batch_size']
        }

        extract_reviews = PlayStoreReviewOperator(
                            task_id='fetch_{}_reviews'.format(app['app_name']),
                            **review_config)

        gcs_path = 'reviews/play_store/{}/'.format(app['app_name']) + \
                    'reviews_{{ execution_date.format("%Y%m%d") }}.json'

        upload_to_gcs = FileToGoogleCloudStorageOperator(
            task_id='upload_{}_to_gcs'.format(app['app_name']),
            src=output_path.path,
            dst=gcs_path,
            bucket=Variable.get('gcs_bucket'),
            google_cloud_storage_conn_id='gcp_conn'
        )

        load_to_bq = GoogleCloudStorageToBigQueryOperator(
            task_id='load_{}_to_bq'.format(app['app_name']),
            bucket=Variable.get('gcs_bucket'),
            source_objects=[gcs_path],
            source_format='NEWLINE_DELIMITED_JSON',
            destination_project_dataset_table='sapporo.{}_play_store_reviews' \
                                                .format(app['app_name'] \
                                                    .replace('.', '_')),
            schema_fields=review_schema,
            write_disposition='WRITE_APPEND',
            bigquery_conn_id='gcp_conn',
            google_cloud_storage_conn_id='gcp_conn'
        )

        start_task >> extract_reviews >> \
            upload_to_gcs >> load_to_bq >> wait_task

    finish_task = DummyOperator(
        task_id='finish_fetch_reviews'
    )

    wait_task >> finish_task
