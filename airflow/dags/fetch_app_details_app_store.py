import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow import configuration
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.gcs_download_operator import GoogleCloudStorageDownloadOperator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator
from airflow.contrib.sensors.gcs_sensor import GoogleCloudStorageObjectSensor

from contrib.utils.dag_output_path import DAGOutputPath

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime.combine(datetime.today() - timedelta(days=7), datetime.min.time()),
    'retries' : 5,
    'retry_delay' : timedelta(minutes=10)
}

schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/app_store/app_details.json')

with DAG(
    dag_id='fetch_app_details_app_store',
    schedule_interval='@daily',
    default_args=default_args) as dag:
    
    start_task = DummyOperator(
        task_id='start_fetch_app_details'
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

    app_details_schema = json.load(open(schema_path))

    wait_task = DummyOperator(
        task_id='wait_task'
    )

    for app in apps:
        output_path = os.path.join(
                        Variable.get('temp_raw_data'),
                        dag.dag_id,
                        app['app_name'],
                        'app_details_{{ execution_date.format("%Y%m%d") }}.json')

        output_path = DAGOutputPath(output_path)

        scraped_path = 'app_details/{}/'.format(app['app_name']) + \
                    'app_details_{{ execution_date.format("%Y%m%d") }}.json'
        
        gcs_sensor = GoogleCloudStorageObjectSensor(
            task_id='sensor_app_details_{}'.format(app['app_name']),
            bucket=Variable.get('itunes_scraper_bucket'),
            object=scraped_path,
            google_cloud_conn_id='itunes_scraper_conn'
        )
        
        get_app_details = GoogleCloudStorageDownloadOperator(
            task_id='get_app_details_{}'.format(app['app_name']),
            bucket=Variable.get('itunes_scraper_bucket'),
            object=scraped_path,
            filename=output_path.path,
            google_cloud_storage_conn_id='itunes_scraper_conn'
        )

        gcs_path = 'app_details/app_store/{}/'.format(app['app_name']) + \
                    'app_details_{{ execution_date.format("%Y%m%d") }}.json'

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
            destination_project_dataset_table='sapporo.{}_app_store_app_details'\
                                                .format(app['app_name']\
                                                        .replace('.','_')),
            schema_fields=app_details_schema,
            write_disposition='WRITE_APPEND',
            bigquery_conn_id='gcp_conn',
            google_cloud_storage_conn_id='gcp_conn'
        )

        start_task >> gcs_sensor >> \
            get_app_details >> upload_to_gcs >> \
            load_to_bq >> wait_task

    finish_task = DummyOperator(
        task_id='finish_fetch_app_details'
    )

    wait_task >> finish_task