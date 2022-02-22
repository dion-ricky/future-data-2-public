import os
import json
import logging
from datetime import datetime

import pandas as pd
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from contrib.utils.twitter_scraper import TwitterScraper
from crate.utils import safe_cast_to_datetime

class TwitterScraperOperator(BaseOperator):

    template_fields = ('since', 'until')
    ui_color = '#fee8f4'

    @apply_defaults
    def __init__(
        self,
        output_path,
        words = None,
        words_any = None,
        hashtag = None,
        since = None,
        until = None,
        to_account = None,
        from_account = None,
        mention_account = None,
        lang = None,
        display_type = 'Top',
        filter_replies = False,
        min_replies = None,
        min_likes = None,
        min_retweets = None,
        geocode = None,
        limit = float("inf"),
        proximity = False,
        *args,
        **kwargs):
        super(TwitterScraperOperator, self).__init__(*args, **kwargs)
        self.output_path = output_path
        self.since = since
        self.until = until
        self.scraper_options = {
            "words": words,
            "words_any": words_any,
            "hashtag": hashtag,
            "to_account": to_account,
            "from_account": from_account,
            "mention_account": mention_account,
            "lang": lang,
            "display_type": display_type,
            "filter_replies": filter_replies,
            "min_replies": min_replies,
            "min_likes": min_likes,
            "min_retweets": min_retweets,
            "geocode": geocode,
            "limit": limit,
            "proximity": proximity
        }
    
    def execute(self, context):
        logging.info("Start Twitter Scraper operator")

        self.scraper_options.update({
            'since': self.since,
            'until': self.until
        })

        logging.info("Scraping options: \n" + \
            '\n'.join(map(lambda k: f"{k[0]}: {k[1]}",
                            self.scraper_options.items())))
        
        scraper = TwitterScraper(**self.scraper_options)

        results = scraper.get()
        if results is None or len(results) == 0:
            logging.info("Got zero results. Terminating")
            with open(self.output_path,'w') as writer:
                writer.write('')
            return
        
        results = pd.DataFrame(results)
        results['dag_execution_date'] = context['ti'].start_date

        logging.info("Fetched {} tweets".format(len(results)))
        logging.info("Writing results to {}".format(self.output_path))

        results.to_json(self.output_path, orient="records", lines=True,
                        date_unit='s', date_format='epoch')
        
        logging.info("Finished getting tweets")