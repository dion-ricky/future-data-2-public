from datetime import datetime
from typing import List

import pandas as pd
from app_store_scraper import AppStore
from pandas._libs.tslibs import NaTType

class AppStoreReview:
    
    def __init__(
            self,
            country,
            app_name,
            app_id,
            count = 100,
            after = None):
        self.country = country
        self.app_name = app_name
        self.app_id = app_id
        self.count = count
        self.after = after

        self.__review = AppStore(
            country=country,
            app_name=app_name,
            app_id=app_id
        )

    def get(self):
        return self.__get_reviews()

    def __get_reviews(self):
        self.__review.review(how_many=self.count, after=self.after, sleep=0.5)

        return self.__review.reviews

class ReviewsGetter:

    def __init__(
            self,
            country,
            app_name,
            app_id,
            start: datetime = None,
            end: datetime = None,
            batch_size = 100):
        self.reviews = AppStoreReview(country, app_name,
                                        app_id, batch_size,
                                        after=start)
        self.start = start
        self.end = end
    
    def get(self):
        """Helper to get reviews easily"""
        if (self.start is None) | (self.end is None):
            return self.__get()
        else:
            return self.__get_within_datetime_range()
    
    def __get(self):
        res =  self.reviews.get()
        return res

    def __get_within_datetime_range(self) -> List[dict]:
        """Return all reviews within datetime range from `start` to `end`"""
        all_results = []

        id = 0
        prev_count = 0

        while True:
            id += 1
            res = self.reviews.get()
            res = pd.DataFrame(res)
            if len(res) == 0:
                return None
            res = res.sort_values(by='date', ascending=True)
            diff = len(res) - prev_count
            prev_count = len(res)

            print("Batch: {} Fetched: {} reviews".format(id, len(res)))
            print("Got {} more".format(diff))

            res_dict = res[(res['date'] >= self.start) &
                            (res['date'] <= self.end)].to_dict('records')

            if res.iloc[0]['date'] >= self.start \
                and diff != 0:
                continue
            else:
                for r in res_dict:
                    r['date'] = int(r['date'].timestamp()) \
                                if type(r['date']) is not NaTType else None
                    all_results.append(r)

                break

        return all_results