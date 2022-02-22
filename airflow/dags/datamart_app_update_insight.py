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
    'start_date': datetime.combine(datetime.today() - timedelta(days=1), datetime.min.time()),
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='datamart_app_update_insight',
    schedule_interval='0 2 * * *',
    default_args=default_args) as dag:

    start_task = DummyOperator(
        task_id='start_datamart_app_update_insight'
    )

    sensor_warehouse_app_info_fact = ExternalTaskSensor(
        task_id='sensor_warehouse_app_info_fact',
        external_dag_id='warehouse_app_info_fact',
        external_task_id='finish_warehouse_app_info_fact',
        allowed_states=['success'],
        check_existence=True,
        retries=5,
        retry_delay=timedelta(minutes=15)
    )

    start_task >> sensor_warehouse_app_info_fact

    sql_app_update_insight = """#standardSQL
    SELECT
        wad.app_id,
        wad.alt_app_id,
        wad.version,
        wad.platform,
        wa.rating,
        wa.rating_count,
        wa.review_count,
        TIMESTAMP(DATETIME(wd.`year`, wd.`month`, wd.`date`, td.`hour`, td.`minute`, td.`second`), "UTC") AS updated_date
    FROM
        sapporo_warehouse.app_info wa
    LEFT JOIN sapporo_warehouse.app_dim wad ON
        wa.app_key = wad.id
    LEFT JOIN sapporo_warehouse.date_dim wd ON
        wa.updated_date_key = wd.date_key 
    LEFT JOIN sapporo_warehouse.time_dim td ON
        wa.updated_time_key = td.time_key;
    """

    datamart_app_update_insight = BigQueryOperator(
        task_id='datamart_app_update_insight',
        sql=sql_app_update_insight,
        destination_dataset_table='sapporo_mart.app_update_insight',
        write_disposition='WRITE_TRUNCATE',
        allow_large_results=True,
        bigquery_conn_id='gcp_conn',
        use_legacy_sql=False
    )

    finish_task = DummyOperator(
        task_id='finish_datamart_app_update_insight'
    )

    sensor_warehouse_app_info_fact >> datamart_app_update_insight >> finish_task