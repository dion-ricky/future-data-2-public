import os
import json
import logging
from datetime import datetime

import pandas as pd
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from contrib.utils.app_store_review import ReviewsGetter

class AppStoreReviewOperator(BaseOperator):
    
    template_fields = ('output_path', 'start', 'end')
    ui_color = '#fee8f4'

    @apply_defaults
    def __init__(
            self,
            output_path,
            app_name,
            app_id,
            country,
            start = None,
            end = None,
            batch_size = 100,
            *args,
            **kwargs):
        super(AppStoreReviewOperator, self).__init__(*args, **kwargs)
        self.output_path = output_path
        self.app_name = app_name
        self.app_id = app_id
        self.country = country
        self.start = start
        self.end = end
        self.batch_size = batch_size
    
    def execute(self, context):
        logging.info("Start AppStore reviews operator")

        start = datetime.fromtimestamp(int(self.start))
        end = datetime.fromtimestamp(int(self.end))

        logging.info(
            "Getting reviews from {start} to {end} with batch of {batch}" \
                .format(
                    start=start.strftime("%Y-%m-%d %H:%M:%S"),
                    end=end.strftime("%Y-%m-%d %H:%M:%S"),
                    batch=self.batch_size
                ))
        
        reviews = ReviewsGetter(self.country, self.app_name, self.app_id,
                                    start, end, batch_size=self.batch_size)

        results = reviews.get()
        if results is None:
            logging.info("Got zero results. Terminating")
            with open(self.output_path,'w') as writer:
                writer.write('')
            return
        results = pd.DataFrame(results)

        results['dag_execution_date'] = context['ti'].start_date

        logging.info("Fetched {} reviews".format(len(results)))
        logging.info("Writing results to {}".format(self.output_path))

        results.to_json(self.output_path, orient="records", lines=True,
                        date_unit='s', date_format='epoch')

        logging.info("Finished getting reviews")