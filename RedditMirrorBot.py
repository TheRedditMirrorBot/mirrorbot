# -*- encoding: utf-8 -*-

from configparser import ConfigParser
from json import load, dump
from os import getpid, listdir, remove, path, makedirs, rename
from shutil import rmtree
from prawcore.exceptions import RequestException, ServerError
from time import sleep, ctime, time
from requests import get
from copy import copy

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
}

def cleanup_init():
    if not path.exists("Media/"):
        makedirs("Media/")
        logger.debug("Media path doesn't exist, created it.")
        return
    
    else:
        rmtree("Media/")
        makedirs("Media/")
        logger.debug("Cleaned Media path")
        return
            

def cleanup(path):
    if path[-1] != "/":
        path += "/"
    
    logger.debug("Cleanup " + path)
    
    if not path.exists(path):
        logging.debug("Cleanup: " + path + " does not exist. Creating it.")
        makedirs(path)
        return
    
    else:
        rmtree(path)
        logging.debug("Cleanup: " + path + " successfully removed.")
        return

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
# Returns true if successful
def download_video(url, sub_id=None, working_dir):
    logger.info("Downloading " + url)
    output_filename = working_dir + "video.mp4"
    opts = copy(ydl_opts)
    opts['outtmpl'] = output_filename
    yt = youtube_dl.YoutubeDL(opts)
    # Twitter post
    if "twitter" in url:
        logger.info('Twitter video detected.')
        response = yt.extract_info(url, process=False)
        
        try:
            while response.get("url"):
                response = yt.extract_info(response["url"], process=False)
        
        except youtube_dl.utils.DownloadError:
            logger.error("Twitter Youtube-dl download error. Unable to download video from URL.")
            return False
            
        url = response["webpage_url"]

    # Reddit video, only entered if sub_id exists (won't be used for comment mirroring)
    elif "v.redd.it" in url and sub_id:
        if download_reddit_video(url, sub_id, working_dir, output_filename):
            logger.info(url + " successfully downloaded.")
        else:
            logger.error(url + " was unable to be downloaded.")
    
    # Otherwise, download normally
    else:
        try:
            yt.download([url])
        except (youtube_dl.utils.DownloadError) as e:
            logger.error("Download error: " + str(e))
            return False
        except (youtube_dl.utils.SameFileError) as e:
            logger.error("Download error: " + str(e))
            return False
        except (UnicodeDecodeError) as e:
            logger.error("Download error: " + str(e))
            return False
    
    return True

# Attempts to download a reddit-hosted video.
# Returns true if successful
def download_reddit_video(url, sub_id, working_dir, output_filename):
    sub = reddit.submission(id=sub_id)
    if sub.media is None:
        if hasattr(sub, "crosspost_parent"):
            sub.media = reddit.submission(sub.crosspost_parent[3:]).media
        else:
            url = get(sub.url).url
            _id = praw.models.reddit.submission.Submission.id_from_url(url)
            sub.media = reddit.submission(_id).media
    
    # Time added to filename to avoid processes writing over each other
    video_url = sub.media["reddit_video"]["fallback_url"]
    video_name = working_dir + (time()) + "_video"
    download(video_name, video_url)
    
    audio_url = video_url.rsplit("/", 1)[0] + "/audio"
    audio_name = working_dir + str(time()) + "_audio"
    download(audio_name, audio_url)

    if sub.media["reddit_video"]["is_gif"]:
        logger.debug("Reddit video is a gif.")
        rename(video_name, output_filename)
    
    #if not gif but still no audio
    elif not 'octet-stream' in magic.Magic(mime=True,uncompress=True).from_file('Media/audio'):
        logger.debug("Reddit video has no audio.")
        rename(video_name, output_filename)
    
    #audio exists
    else:
        logger.debug("Running combine_media() on reddit video.")
        combine_media(video_name, audio_name, output_filename)
        logger.debug("Media combining complete.")

    return True

def combine_media(video, audio, output_filename):
    output = str(time()) + "_output.mp4"
    command = [
        "ffmpeg",
        "-v", "quiet",
        "-i", "Media/" + video,
        "-i", "Media/" + audio,
        "-c", "copy",
        "-f", "mp4",
        "Media/" + output,
        "-y"
    ]

    subprocess.run(command)


def download(filename, url):
    with open("Media/" + filename, "wb") as file:
        file.write(get(url).content)

#converts given file to mp4, and returns new filename
def conv_to_mp4(file_name):
    
    vid_name = file_name[:-4] + ".mp4"
    
    ##check if file is mkv and convert to mp4
    if ".mkv" in file_name:
        ffmpeg_subproc = [
            "ffmpeg",
            "-i", file_name,
            "-strict", "-2", #fixes opus experimental error
            "-vcodec", "copy",
            "-y",
            vid_name
            ]
        conv_process = subprocess.run(ffmpeg_subproc)
        return vid_name

    else:
        return file_name

def upload_video(file_name, _id):
    file_name = conv_to_mp4(file_name)
    logger.debug("Uploading to DO...")
    save_file_size(file_name)
    logger.debug("Size:", str(os.path.getsize(file_name)/1024/1024) + "MB")
    client = session.client('s3',
        region_name='nyc3',
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=do_access_id,
        aws_secret_access_key=do_secret_key)
    key = "videos/" + str(_id) + ".mp4"

    try:
        client.upload_file(file_name, 'pf-mirror-1', key)
    except (boto3.S3UploadFailedError) as e:
        logger.error(_id + " failed to upload: " + str(e))
        return None
    
    logger.debug(_id + " successfully uploaded.")
    
    resource = boto3.resource('s3',
        region_name='nyc3',
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=do_access_id,
        aws_secret_access_key=do_secret_key)

    logger.debug("DO key: " + key)
    client.put_object_acl(ACL='public-read', Bucket='pf-mirror-1', Key=key)
    key = "videos/" + key
    mirror_url = "https://pf-mirror-1.nyc3.digitaloceanspaces.com/" + key
    
    logger.info("Upload complete!")
    return str(mirror_url)


# Takes in a submission object and attempts to mirror it
# Returns true if mirror was successful
def mirror_submission(submission):
    working_dir = "Media/" + str(time()) + "_dl/"
    cleanup(working_dir)
    download_video(submission.url, submission.id, working_dir)
    mirror_url = upload_video(working_dir + "video.mp4", submission.id)
    

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
            logger.debug("Got next post: ", submission.title, " ", "https://reddit.com" + submission.permalink + "\n" + submission.url)

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
    cleanup_init()
    if path.exists("/usr/bin/ffmpeg"):
        print(main())
    else:
        print("Needs ffmpeg")
