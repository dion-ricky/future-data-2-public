import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow import configuration
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator

from crate.utils import TweetDisplayType

from contrib.utils.dag_output_path import DAGOutputPath
from contrib.operators.twitter_scraper_operator import TwitterScraperOperator

default_args = {
    'owner': 'dion-ricky',
    'start_date': datetime.combine(datetime.today() - timedelta(days=7), datetime.min.time()),
    'retries': 5,
    'retry_delay': timedelta(minutes=10)
}

schema_path = os.path.join(configuration.get("core", "dags_folder"),
                            'schemas/bigquery/play_store/reviews.json')

with DAG(
    dag_id='fetch_tweets_by_keyword',
    schedule_interval='@daily',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_fetch_tweets'
    )

    tweet_schema = json.load(open(schema_path))

    wait_task = DummyOperator(
        task_id='wait_task'
    )

    tweet_params = [
        {
            'app_name': 'blibli',
            'words_any': ['blibli']
        },
        {
            'app_name': 'tokopedia',
            'words_any': ['tokopedia', 'tokped', 'toped']
        },
        {
            'app_name': 'shopee',
            'words_any': ['shopee']
        },
        {
            'app_name': 'bukalapak',
            'words_any': ['bukalapak']
        },
        {
            'app_name': 'lazada',
            'words_any': ['lazada']
        },
        {
            'app_name': 'jdid',
            'words_any': ['jdid', 'jd.id']
        },
        {
            'app_name': 'zalora',
            'words_any': ['zalora']
        },
        {
            'app_name': 'bhinneka',
            'words_any': ['bhinneka']
        },
        {
            'app_name': 'elevenia',
            'words_any': ['elevenia']
        }
    ]

    default_params = {
        'lang': 'id',
        'display_type': TweetDisplayType.TOP,
        'filter_replies': True,
        'since': '{{ execution_date.format("%Y-%m-%d") }}',
        'until': '{{ execution_date.add(days=1).format("%Y-%m-%d") }}'
    }

    for param in tweet_params:
        d = default_params

        output_path = os.path.join(
                        Variable.get('temp_raw_data'),
                        dag.dag_id,
                        param['app_name'],
                        "tweets_{{ execution_date.format('%Y%m%d') }}.json")
        
        output_path = DAGOutputPath(output_path)

        config = {
            'output_path': output_path.path,
            'words_any': param['words_any'],
            'lang': d['lang'],
            'display_type': d['display_type'],
            'filter_replies': d['filter_replies'],
            'since': d['since'],
            'until': d['until']
        }

        scrape_tweet = TwitterScraperOperator(
            task_id='scrape_{}_tweets'.format(param['app_name']),
            **config
        )

        gcs_path = 'tweets/{}/'.format(param['app_name']) + \
                        'tweet_{{ execution_date.format("%Y%m%d") }}.json'
        
        # upload_to_gcs = FileToGoogleCloudStorageOperator(
        #     task_id='upload_{}_tweet_to_gcs'.format(param['app_name']),
        #     src=output_path.path,
        #     dst=gcs_path,
        #     bucket=Variable.get('gcs_bucket'),
        #     google_cloud_storage_conn_id='gcp_conn'
        # )

        # load_to_bq = GoogleCloudStorageToBigQueryOperator(
        #     task_id='load_{}_tweet_to_bq'.format(param['app_name']),
        #     bucket=Variable.get('gcs_bucket'),
        #     source_objects=[gcs_path],
        #     source_format='NEWLINE_DELIMITED_JSON',
        #     destination_project_dataset_table='sapporo.{}_tweet' \
        #                                         .format(param['app_name'] \
        #                                             .replace('.', '_')),
        #     schema_fields=tweet_schema,
        #     write_disposition='WRITE_APPEND',
        #     bigquery_conn_id='gcp_conn',
        #     google_cloud_storage_conn_id='gcp_conn'
        # )

        start_task >> scrape_tweet >> \
            wait_task
            # upload_to_gcs >> \
            # load_to_bq >> \
    
    finish_task = DummyOperator(
        task_id='finish_fetch_tweets'
    )

    wait_task >> finish_task