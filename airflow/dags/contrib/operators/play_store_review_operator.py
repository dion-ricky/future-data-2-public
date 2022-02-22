import os
import json
import logging
from datetime import datetime

import pandas as pd
from google_play_scraper import Sort
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from contrib.utils.play_store_review import ReviewsGetter

class PlayStoreReviewOperator(BaseOperator):

    template_fields = ('output_path', 'start', 'end')
    ui_color = '#fee8f4'

    @apply_defaults
    def __init__(
            self,
            output_path,
            app_id,
            lang,
            country,
            start = None,
            end = None,
            batch_size = 100,
            sort = Sort.NEWEST,
            *args,
            **kwargs):
        super(PlayStoreReviewOperator, self).__init__(*args, **kwargs)
        self.output_path = output_path
        self.app_id = app_id
        self.lang = lang
        self.country = country
        self.start = start
        self.end = end
        self.batch_size = batch_size
        self.sort = sort

    def execute(self, context):
        logging.info("Start Google Play Store reviews operator")

        start = datetime.fromtimestamp(int(self.start))
        end = datetime.fromtimestamp(int(self.end))

        logging.info(
            "Getting reviews from {start} to {end} with batch of {batch}" \
                .format(
                    start=start.strftime("%Y-%m-%d %H:%M:%S"),
                    end=end.strftime("%Y-%m-%d %H:%M:%S"),
                    batch=self.batch_size
                ))
        
        reviews = ReviewsGetter(self.app_id, self.lang, self.country,
                                    start, end, batch_size=self.batch_size,
                                    sort=self.sort)

        results = reviews.get()
        results = pd.DataFrame(results)

        results['dag_execution_date'] = context['ti'].start_date

        logging.info("Fetched {} reviews".format(len(results)))
        logging.info("Writing results to {}".format(self.output_path))

        results.to_json(self.output_path, orient="records", lines=True,
                        date_unit='s', date_format='epoch')

        logging.info("Finished getting reviews")