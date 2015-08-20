#!/usr/bin/env python3

import time

import tweepy

from models import twitter_access_token, twitter_access_secret, twitter_consumer_secret, twitter_consumer_key, tweet_queue


auth = tweepy.OAuthHandler(twitter_consumer_key.get(), twitter_consumer_secret.get())
auth.set_access_token(twitter_access_token.get(), twitter_access_secret.get())
api = tweepy.API(auth)

if __name__ == "__main__":
    while True:
        if len(tweet_queue) > 0:
            tweet = tweet_queue.popleft().decode()
            api.update_status(tweet)
        time.sleep(1)
