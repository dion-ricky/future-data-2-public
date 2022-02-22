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

def extract_bool(row, col):
    r = row[col]
    try:
        r = bool(r)
    except Exception:
        r = False
    finally:
        return r

def full_date_process(row, col):
    r = row[col]
    try:
        ts = ((r - 25569) * 86400)
        r = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        raise
    finally:
        return r

def weekday_flag_process(row, col):
    r = row[col]
    try:
        r = True if r == 'Weekday' else False
    except Exception:
        r = False
    finally:
        return r

def preprocess(file_path, output_path):
    df = pd.read_csv(open(file_path, 'r'), sep=';')

    int_cols = ["date", "month", "quarter", "year", "day of week", "week num in year", "yearmo"]

    df['full date'] = df.apply(lambda row: full_date_process(row, 'full date'), axis=1)

    df['weekday flag'] = df.apply(lambda row: weekday_flag_process(row, 'weekday flag'), axis=1)
    
    for col in int_cols:
        df[col] = df.apply(lambda row: extract_int(row, col), axis=1)

    nulls = pd.DataFrame([[-1, None, None, None, None, None, None, None, None, None, None, None, None, None]],
                columns=['date key', 'full date',
                        'day of week', 'date',
                        'day name', 'day abbrev',
                        'weekday flag', 'week num in year',
                        'month', 'month name',
                        'month abbrev', 'quarter',
                        'year', 'yearmo'])
    
    df.append(nulls)

    columns_mapper = {
        'date key': 'date_key',
        'full date': 'full_date',
        'day of week': 'day_of_week',
        'date': 'date',
        'day name': 'day_name',
        'day abbrev': 'day_abbrev',
        'weekday flag': 'weekday_flag',
        'week num in year': 'week_num_in_year',
        'month': 'month',
        'month name': 'month_name',
        'month abbrev': 'month_abbrev',
        'quarter': 'quarter',
        'year': 'year',
        'yearmo': 'yearmo'
    }

    df.rename(columns=columns_mapper, inplace=True)

    df.to_json(output_path, orient='records', lines=True)

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime(2021, 10, 10),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='date_dimension',
    description="DAG to process ETL Date Dimension",
    schedule_interval='@once',
    default_args=default_args) as dag:

    output_path = os.path.join(
                        Variable.get('temp_raw_data'),
                        dag.dag_id,
                        'date_dim_{{ execution_date.format("%Y%m%d") }}.json')
        
    output_path = DAGOutputPath(output_path)

    start = DummyOperator(
        task_id="start"
    )

    date_file_path = os.path.join('/opt/datasets', 'dim_date.csv')

    export_date_data_task = PythonOperator(
        task_id='export_date_data',
        python_callable=preprocess,
        op_kwargs={'file_path': date_file_path,
                    'output_path': output_path.path}
    )

    # upload
    gcs_path = 'dimensions/date_{{ execution_date.format("%Y%m%d") }}.json'

    upload_to_gcs = FileToGoogleCloudStorageOperator(
        task_id='upload_to_gcs',
        src=output_path.path,
        dst=gcs_path,
        bucket=Variable.get('gcs_bucket'),
        google_cloud_storage_conn_id='gcp_conn'
    )

    # load
    schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/dimension/date.json')
    date_bq_schema = json.load(open(schema_path, 'r'))

    load_to_bq = GoogleCloudStorageToBigQueryOperator(
        task_id='load_to_bq',
        bucket=Variable.get('gcs_bucket'),
        source_objects=[gcs_path],
        source_format='NEWLINE_DELIMITED_JSON',
        destination_project_dataset_table='sapporo_staging.date_dim',
        schema_fields=date_bq_schema,
        write_disposition='WRITE_TRUNCATE',
        bigquery_conn_id='gcp_conn',
        google_cloud_storage_conn_id='gcp_conn'
    )

    finish =  DummyOperator(
        task_id="finish"
    )

    start >> export_date_data_task >> upload_to_gcs >> \
        load_to_bq >> finish