from datetime import datetime
from typing import List, Optional, Union

import pandas as pd
from pandas._libs.tslibs import NaTType

from crate import Scraper, ScraperOptions, TweetDisplayType
from crate.driver import DriverOptions

class TwitterScraper:
    def __init__(
        self,
        words: Optional[Union[str, List[str]]] = None,
        words_any: Optional[Union[str, List[str]]] = None,
        hashtag: Optional[str] = None,
        since: Optional[Union[datetime, str]] = None,
        until: Optional[Union[datetime, str]] = None,
        to_account: Optional[str] = None,
        from_account: Optional[str] = None,
        mention_account: Optional[Union[str, List[str]]] = None,
        lang: Optional[str] = None,
        display_type: \
            Optional[Union[TweetDisplayType, str]] = TweetDisplayType.TOP,
        filter_replies: Optional[bool] = False,
        min_replies: Optional[int] = None,
        min_likes: Optional[int] = None,
        min_retweets: Optional[int] = None,
        geocode: Optional[str] = None,
        limit: Optional[int] = float("inf"),
        proximity: Optional[bool] = False
        ) -> None:
        driver_options = DriverOptions(
            driver_path='/opt/airflow/chromedriver'
        )

        self.scraper = Scraper(options=driver_options)

        self.scraper_options = ScraperOptions(
            words=words,
            words_any=words_any,
            hashtag=hashtag,
            since=since,
            until=until,
            to_account=to_account,
            from_account=from_account,
            mention_account=mention_account,
            lang=lang,
            display_type=display_type,
            filter_replies=filter_replies,
            min_replies=min_replies,
            min_likes=min_likes,
            min_retweets=min_retweets,
            geocode=geocode,
            limit=limit,
            proximity=proximity
        )

    def get(self) -> List:
        return self.__get(self.scraper_options)
    
    def __get(self, scraper_options: ScraperOptions) -> List:
        return self.scraper.scrape(scraper_options)