from datetime import datetime
from typing import List
from time import sleep

import pandas as pd
from google_play_scraper import Sort, reviews
from pandas._libs.tslibs import NaTType

class PlayStoreReview:
    
    def __init__(
            self,
            app_id,
            lang,
            country,
            count = 100,
            sort = Sort.NEWEST):
        self.app_id = app_id
        self.lang = lang
        self.country = country
        self.count = count
        self.sort = sort
        self.__continuation_token = None

        self._params = {
            'app_id': self.app_id,
            'lang': self.lang,
            'country': self.country,
            'count': self.count,
            'sort': self.sort,
            'continuation_token': self.__continuation_token
        }

    def get(self):
        return self.__get_reviews()

    def __get_reviews(self):

        result, continuation_token = reviews(
            **self._params
        )

        self.__continuation_token = continuation_token
        self._params['continuation_token'] = continuation_token

        return result, continuation_token

class ReviewsGetter:

    def __init__(
            self,
            app_id,
            lang,
            country,
            start: datetime = None,
            end: datetime = None,
            batch_size = 100,
            sort = Sort.NEWEST):
        self.reviews = PlayStoreReview(app_id, lang,
                                        country, batch_size, sort)
        self.start = start
        self.end = end
    
    def get(self):
        """Helper to get reviews easily"""
        if (self.start is None) | (self.end is None):
            return self.__get()
        else:
            return self.__get_within_datetime_range()
    
    def __get(self):
        res, _ =  self.reviews.get()
        return res

    def __get_within_datetime_range(self) -> List[dict]:
        """Return all reviews within datetime range from `start` to `end`"""
        all_results = []

        id = 0
        retry_count = 0
        max_retry = 15

        while True:
            id += 1
            res, _ = self.reviews.get()
            res = pd.DataFrame(res)
            if len(res) == 0:
                retry_count += 1
                if retry_count > max_retry:
                    print("Got zero results. Max retries reached. Exiting ...")
                    break

                print("Got zero results, retrying ...")
                print("Retry {}/{}".format(retry_count, max_retry))
                
                pause_duration = 60 + (5 * retry_count * 1.5)
                print("Pausing for {} seconds".format(pause_duration))
                sleep(pause_duration)
                
                print("Retrying ...")
                continue

            res = res.sort_values(by='at', ascending=True)

            print("Batch: {} Fetched: {} reviews".format(id, len(res)))

            res_dict = res[(res['at'] >= self.start) &
                            (res['at'] <= self.end)].to_dict('records')
            for r in res_dict:
                r['at'] = int(r['at'].timestamp()) \
                             if type(r['at']) is not NaTType else None
                r['repliedAt'] = int(r['repliedAt'].timestamp()) \
                                    if type(r['repliedAt']) is not NaTType \
                                        and r['repliedAt'] is not None \
                                        else None
                all_results.append(r)
            
            if res.iloc[0]['at'] >= self.start:
                continue
            else:
                break

        return all_results