import json
import logging
from datetime import datetime

import pandas as pd
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

class JsonToNdjsonOperator(BaseOperator):

    template_fields = ('json_path', 'output_path')
    ui_color = '#fee8f4'
    
    @apply_defaults
    def __init__(
            self,
            json_path,
            output_path,
            json_orient='columns',
            encoding='utf-8',
            *args,
            **kwargs):
        super(JsonToNdjsonOperator, self).__init__(*args, **kwargs)
        self.json_path = json_path
        self.output_path = output_path
        self.encoding = encoding
        self.json_orient = json_orient
    
    def execute(self, context):
        logging.info("Start transform JSON to NDJSON")

        json_file = open(self.json_path, 'r', encoding=self.encoding)

        df = pd.DataFrame.from_dict(json.load(json_file), orient=self.json_orient)
        
        logging.info("Writing NDJSON to {}".format(self.output_path))

        df.to_json(self.output_path, orient='records', lines=True,
                    date_unit='s', date_format='epoch')

        json_file.close()
        
        logging.info("Finished transforming JSON to NDJSON")