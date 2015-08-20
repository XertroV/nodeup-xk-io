#!/usr/bin/env python3

import time
import logging

import tweepy

from models import twitter_access_token, twitter_access_secret, twitter_consumer_secret, twitter_consumer_key, tweet_queue

logging.basicConfig(level=logging.INFO)

def get_api():
    auth = tweepy.OAuthHandler(twitter_consumer_key.get(), twitter_consumer_secret.get())
    auth.set_access_token(twitter_access_token.get(), twitter_access_secret.get())
    return tweepy.API(auth)


if __name__ == "__main__":
    api = get_api()
    while True:
        if len(tweet_queue) > 0:
            tweet = tweet_queue.popleft().decode()
            try:
                logging.info('Tweeting %s' % repr(tweet))
                logging.info(str(type(tweet)))
                api.update_status(status=tweet)
            except Exception as e:
                tweet_queue.prepend(tweet)
                logging.error('Tweet failed: %s gave error %s' % (tweet, repr(e)))
                raise e
        time.sleep(5)
