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

# Listens for POST requests to create new mirrors
def network_listener():
    

# Watches for new subreddit submissions, and attempts to mirror them
def sub_watcher():
    
    
# Watches for new comments containing !mirror, and mirrors the parent comment's video if possible
def comment_watcher():
    

# Manages POST listener, comment watcher, and sub watcher
def main():
    

if __name__ == "__main__":
    if path.exists("/usr/bin/ffmpeg"):
        print(main())
    else:
        print("Needs ffmpeg")
