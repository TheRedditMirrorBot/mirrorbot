# -*- encoding: utf-8 -*-

from configparser import ConfigParser
from json import load, dump
from os import getpid, listdir, remove, path, makedirs
from prawcore.exceptions import RequestException, ServerError
from time import sleep, ctime, time
from requests import get

import logging
import praw
import re
import subprocess
import youtube_dl
import os
import simplejson as json
import requests
import threading
import urllib.parse

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create log file handler
handler = logging.FileHandler('mirrorbot.log')
handler.setLevel(logging.DEBUG)

# Create logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.debug('Logging initialized.')

logger.debug("Opening config")
config = ConfigParser()
config.read("config.ini")
logger.debug("Config opened")

do_access_id = config["DigitalOcean"]["access_id"]
do_secret_key = config["DigitalOcean"]["secret_key"]
do_bucket_name = config["DigitalOcean"]["bucket_name"]
specified_sub = config["Reddit"]["sub_to_mirror"]
specified_host = config["General"]["backend_host"]

# Logger class for youtube_dl
class MyLogger(object):
    def debug(self, msg):
        logger.debug(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msgs)

ydl_opts = {
    'format': 'best[ext=webm]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'logger': MyLogger(),
    'outtmpl': "Media/%(id)s.mp4",
}

def cleanup_network():
    logger.info("Cleanup")
    if not path.exists("Media/network"):
        makedirs("Media/network")
    
    for file in listdir("Media/network"):
        remove("Media/network/" + file)

def cleanup_submissions():
    logger.info("Cleanup")
    if not path.exists("Media/submission"):
        makedirs("Media/submission")
    
    for file in listdir("Media/submission"):
        remove("Media/submission/" + file)

def cleanup_comments():
    logger.info("Cleanup")
    if not path.exists("Media/comment"):
        makedirs("Media/comment")
    
    for file in listdir("Media/comment"):
        remove("Media/comment/" + file)

# Returns true if a video for the submission already exists, false otherwise
def is_submission_mirrored(submission):
    video_list = get_sub_video_list(do_bucket_name)
    return (submission.id in video_list)
    

# Takes an s3 bucket object as input
# Returns a list of reddit submission IDs for which videos exist
def get_sub_video_list(bucket_name):
    bucket = get_bucket(bucket_name)
    logger.debug("get_video_list()")
    regex = re.compile('/\w*\.', re.IGNORECASE)
    raw_text = str([x for x in bucket.objects.all()])
    video_list = regex.findall(raw_text)
    
    return [x[1:-1] for x in video_list]

# Returns an object representing the specified bucket
def get_bucket(bucket_name):
    logger.debug("Creating s3 resource object")
    resource = boto3.resource('s3',
        region_name='nyc3',
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=do_access_id,
        aws_secret_access_key=do_secret_key)
    
    return resource.Bucket(bucket_name)

# Takes in a url and attempts to download the video
def download_video(url):
    logger.info("Downloading " + url)
    logger.debug("Got next post: ", submission.title, " ", "https://reddit.com" + submission.permalink + "\n" + submission.url)
    
    #Don't wanna mirror nazi propaganda
    if "Antifa" in submission.title or "antifa" in submission.title:
        return
    

# Takes in a submission object and attempts to mirror it
# Returns true if mirror was successful
def mirror_submission(submission):
    

# Listens for POST requests to create new mirrors
def network_listener():
    

# Watches for new subreddit submissions, and attempts to mirror them
def sub_watcher():
    reddit = praw.Reddit(**config["Reddit"])
    stream = reddit.subreddit(sub_to_mirror).stream.submissions(pause_after=1)
    
    while True:
        cleanup_submissions()
        try:
            # Get next post
            submission = next(stream)
        except RequestException:
            # Client side error
            logger.error("RequestException in sub_watcher")
            sleep(60)
        except ServerError:
            # Reddit side error
            logger.error("ServerError in sub_watcher")
            sleep(60)
        except StopIteration:
            logger.error("StopIteration in sub_watcher")
            break
        else:
            if submission is None:
                logger.info("No new posts.")
                continue

            if submission.is_self:
                logger.info("Skipping self-post.")
                continue

            # Don't bother creating mirror for posts over a month old
            if submission.created_utc < time() - 3600 * 24 * 30:
                logger.info("Submission is too old.")
                continue

            if is_submission_mirrored(submission):
                logger.info("Submission already mirrored.")
                continue
            if mirror_submission(submission):
                logger.info(submission.id + " successfully mirrored!")
                continue
            else:
                logger.error("Something went wrong with " + submission.id + ". Check the logs for info.")
                continue
            cleanup_submissions()
                
    
# Watches for new comments containing !mirror, and mirrors the parent comment's video if possible
def comment_watcher():
    

# Manages POST listener, comment watcher, and sub watcher
def main():
    jobs = []
    # sub_watcher
    jobs.append(multiprocessing.Process(name="Submissions:", target=sub_watcher))
    # comment_watcher
    jobs.append(multiprocessing.Process(name="Comments:", target=comment_watcher))
    # network listener
    jobs.append(multiprocessing.Process(name="Network:", target=network_listener))
    
    # start threads
    for job in jobs:
        job.start()

if __name__ == "__main__":
    if path.exists("/usr/bin/ffmpeg"):
        print(main())
    else:
        print("Needs ffmpeg")
