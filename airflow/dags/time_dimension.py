import os
import json
from datetime import timedelta, datetime

import pandas as pd
from airflow import DAG
from airflow import configuration

from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator

from contrib.utils.dag_output_path import DAGOutputPath

def extract_int(row, col):
    r = row[col]
    try:
        r = int(r)
    except Exception:
        r = 0
    finally:
        return r

def preprocess(file_path, output_path):
    df = pd.read_csv(open(file_path, 'r'), sep=',')

    int_cols = ["time_key", "hour", "minute", "second"]

    for col in int_cols:
        df[col] = df.apply(lambda row: extract_int(row, col), axis=1)

    nulls = pd.DataFrame([[-1, None, None, None, None, None, None]],
                columns=["time_key", "time_id", "hour", "minute",
                            "second", "meridiem", "time_of_day"])

    df.append(nulls)

    df.to_json(output_path, orient='records', lines=True)

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime(2021, 10, 10),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='time_dimension',
    description="DAG to process ETL Time Dimension",
    schedule_interval='@once',
    default_args=default_args) as dag:

    output_path = os.path.join(
                        Variable.get('temp_raw_data'),
                        dag.dag_id,
                        'time_dim_{{ execution_date.format("%Y%m%d") }}.json')
        
    output_path = DAGOutputPath(output_path)

    start = DummyOperator(
        task_id="start"
    )

    time_file_path = os.path.join('/opt/datasets', 'dim_time.csv')

    export_time_task = PythonOperator(
        task_id='export_time_data',
        python_callable=preprocess,
        op_kwargs={'file_path': time_file_path,
                    'output_path': output_path.path}
    )

    # upload
    gcs_path = 'dimensions/time_{{ execution_date.format("%Y%m%d") }}.json'

    upload_to_gcs = FileToGoogleCloudStorageOperator(
        task_id='upload_to_gcs',
        src=output_path.path,
        dst=gcs_path,
        bucket=Variable.get('gcs_bucket'),
        google_cloud_storage_conn_id='gcp_conn'
    )

    # load
    schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/dimension/time.json')
    time_bq_schema = json.load(open(schema_path, 'r'))

    load_to_bq = GoogleCloudStorageToBigQueryOperator(
        task_id='load_to_bq',
        bucket=Variable.get('gcs_bucket'),
        source_objects=[gcs_path],
        source_format='NEWLINE_DELIMITED_JSON',
        destination_project_dataset_table='sapporo_staging.time_dim',
        schema_fields=time_bq_schema,
        write_disposition='WRITE_TRUNCATE',
        bigquery_conn_id='gcp_conn',
        google_cloud_storage_conn_id='gcp_conn'
    )

    finish =  DummyOperator(
        task_id="finish"
    )

    start >> export_time_task >> upload_to_gcs >> \
        load_to_bq >> finish