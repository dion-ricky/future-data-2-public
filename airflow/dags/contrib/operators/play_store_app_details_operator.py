import os
import json
import logging
from datetime import datetime

from google_play_scraper import app
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

class PlayStoreAppDetailsOperator(BaseOperator):

    template_fields = ('output_path',)
    ui_color = '#fee8f4'

    @apply_defaults
    def __init__(
            self,
            output_path: str,
            app_id: str,
            lang: str,
            country: str,
            *args,
            **kwargs):
        super(PlayStoreAppDetailsOperator, self).__init__(*args, **kwargs)
        self.output_path = output_path
        self.app_id = app_id
        self.lang = lang
        self.country = country
    
    def execute(self, context):
        logging.info("Start Google Play Store app details operator")

        logging.info("Fetching <{id} {lang} {country}> " \
                        .format(id=self.app_id, lang=self.lang,
                                country=self.country) +
                        "app details from scraper")

        result = app(self.app_id, self.lang, self.country)
        result['dag_execution_date'] = context['ti'].start_date \
                                        .strftime("%Y-%m-%d %H:%M:%S")

        logging.info("Writing app details to {}".format(self.output_path))

        with open(self.output_path, 'w') as _f:
            _f.write(json.dumps(result))
        
        logging.info("Finished fetching app details")