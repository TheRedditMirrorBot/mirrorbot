# -*- encoding: utf-8 -*-

from configparser import ConfigParser
from json import load, dump
from os import getpid, listdir, remove, path, makedirs
from prawcore.exceptions import RequestException, ServerError
from time import sleep, ctime, time
from requests import get

import praw
import re
import subprocess
import youtube_dl
import os
import simplejson as json
import requests
import threading
import urllib.parse

print(getpid())

# Empty youtube logger
class MyLogger():
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

config = ConfigParser()
config.read("praw.ini")

reddit = praw.Reddit(**config["Reddit"])
auth = config["Streamable"]["username"], config["Streamable"]["password"]
yt = youtube_dl.YoutubeDL({"logger": MyLogger(), "outtmpl": "Media/%(id)s.mp4"})

try:
    with open("saved_links.txt") as file:
        # Load hash file and only keep most recent 28 days
        saved_links = [n for n in load(file) if n["created"] > time() - 3600 * 24 * 28]
except FileNotFoundError:
    with open("saved_links.txt", "w") as file:
        saved_links = []
        dump(saved_links, file)


def check_links(submission):
    mirror_list = []

    if saved_links:
        while saved_links[0]["created"] < time() - 3600 * 24 * 28:
            saved_links.pop(0)

    for data in saved_links:
        if data["video_url"] == submission.url:
            mirror_url = data["mirror_url"]


            if data["mirror_url"]:
                if not ("error" or "supplied") in str(mirror_url):
                    for x in mirror_url.split():
                        mirror_list.append(x.replace("'","").replace("[","").replace("]","").replace(",",""))
                    
                    reply_reddit(submission, mirror_list)
            
            return save("Repost", submission, mirror_list)

def cleanup():
    print("Cleanup")
    if not path.exists("Media"):
        makedirs("Media")

    for file in listdir("Media"):
        remove("Media/" + file)

def combine_media():
    command = [
        "ffmpeg",
        "-v", "quiet",
        "-i", "Media/video",
        "-i", "Media/audio",
        "-c", "copy",
        "-f", "mp4",
        "Media/output.mp4",
        "-y"
    ]

    subprocess.run(command)

def download(filename, url):
    with open("Media/" + filename, "wb") as file:
        file.write(get(url).content)            

def process(submission):
    print("process() entered")
    print("Got next post: ", submission.title, " ", "https://reddit.com" + submission.permalink)
    #Don't wanna mirror nazi propaganda
    if "Antifa" in submission.title or "antifa" in submission.title:
        return
    mirror_url = None
    if check_links(submission):
        print("Reposted old mirror link!")
        return
    
    print("VIDEO URL: "+ submission.url)

    # Twitter post
    if "twitter" in submission.url:
        print("TWEETER VIDEO")
        response = yt.extract_info(submission.url, process=False)
        
        try:
            while response.get("url"):
                response = yt.extract_info(response["url"], process=False)
        
        except youtube_dl.utils.DownloadError:
            return save("Twitter download error", submission)
            

        submission.url = response["webpage_url"]

    # Reddit hosted video
    if submission.domain == "v.redd.it":
        print("LEDDIT VIDEO")
        # If post is crosspost, set submission to linked post
        if submission.media is None:
            if hasattr(submission, "crosspost_parent"):
                submission.media = reddit.submission(submission.crosspost_parent[3:]).media
            else:
                url = get(submission.url).url
                _id = praw.models.reddit.submission.id_from_url(url)
                submission.media = reddit.submission(_id).media

        video_url = submission.media["reddit_video"]["fallback_url"]
        download("video", video_url)

        if submission.media["reddit_video"]["is_gif"]:
            mirror_url = upload("Media/video")
            status = "Complete"
            print("Mirror url: " + str(mirror_url))
            
        
        else:
            audio_url = video_url.rsplit("/", 1)[0] + "/audio"
            download("audio", audio_url)
            combine_media()
            
            mirror_url = upload("Media/output.mp4")
            status = "Complete"
            print("Mirror url: " + str(mirror_url))

        

        if status == "Complete":
            reply_reddit(submission, mirror_url)
            return save(status, submission, mirror_url)
        
    #download video
    try:
        yt.download([submission.url])
    except (youtube_dl.utils.DownloadError) as e:
        print(str(e))
        return save(str(e), submission, "Download error")
    except (youtube_dl.utils.SameFileError) as e:
        print(str(e))
        return save(str(e), submission, "Same file error")

    file = [i for i in listdir("Media")][0]
    file = "Media/" + str(file)
    mirror_url = upload(file)
    if "NOT_HTTP: " in mirror_url:
        print("NOT HTTP")
        return
    else:
        status = "Complete"
        print("Mirror url: " + str(mirror_url))
        reply_reddit(submission, mirror_url)
        return save(status, submission, mirror_url)
     
    # Should never be called
    save("End", submission)            

def reply_reddit(submission, mirror_url):
    print("Submitting comment...")
    while True:
        if not mirror_url:
            return
        try:
            counter = 0
            mirror_text = ""
            for x in mirror_url:
                if not x:
                    continue
                mirror_text += "[Mirror {}](https://dopeslothe.github.io/PublicFreakout-Mirror-Player/?url={}) \n\n".format(counter + 1, urllib.parse.quote(mirror_url[counter], safe=''))
                counter += 1
            comment = submission.reply(" | ".join([
                mirror_text + "  \nI am a bot",
                "[Feedback](https://www.reddit.com/message/compose/?to={[Reddit][host_account]}&subject=PublicFreakout%20Mirror%20Bot)".format(config),
                "[Github](https://github.com/dopeslothe/PublicFreakout-Mirror-Bot) "
            ]))
            comment.mod.approve()
            break
        
        except praw.exceptions.APIException:
            print("Rate limit exception")
            sleep(60)
            continue

def run():
    while True:
        stream = reddit.subreddit("PublicFreakout").stream.submissions(pause_after=1)

        try:
            checked = [n._extract_submission_id() for n in reddit.user.me().comments.new()]
        except RequestException:
            sleep(60)
            continue

        while True:
            cleanup()

            try:
                # Get next post
                submission = next(stream)
            except RequestException:
                # Client side error
                sleep(60)
            except ServerError:
                # Reddit side error
                sleep(60)
            except StopIteration:
                break
            else:
                if submission is None:
                    print("No new posts.")
                    continue

                if submission.is_self:
                    print("Skipping self-post.")
                    continue

                # Don't bother creating mirror for posts over a day old
                if submission.created_utc < time() - 3600 * 24 * 1:
                    print("Submission is too old")
                    continue

                if submission in checked:
                    print("Submission already mirrored")
                    continue

                try:
                    process(submission)
                except PermissionError:
                    return "Permission denied"

            cleanup()

def save_file_size(file_name):
    with open("file_sizes.txt", "a") as file:
        out = str(ctime()) + ": " + str(os.path.getsize(file_name)) + "\n"
        file.write(out)


def save(status, submission, mirror_url=None):
    if not mirror_url:
        print("Unable to save to file: No url supplied")
        return
    text = "{:<19} | " + ctime() + " | https://www.reddit.com{:<85} | {}\n"
    permalink = submission.permalink.encode("ascii", "ignore").decode()

    with open(auth[0] + " log.txt", "a") as file:
        file.write(text.format(status, permalink, " | " + str(mirror_url)))

    saved_links.append({
        "created": int(submission.created_utc),
        "reddit": "https://www.reddit.com" + permalink,
        "video_url": submission.url,
        "mirror_url": str(mirror_url)
    })

    while saved_links[0]["created"] < time() - 3600 * 24 * 28:
        saved_links.pop(0)

    with open("saved_links.txt", "w") as file:
        dump(saved_links, file, indent=4, sort_keys=True)

    return True

#new upload function, doesn't use limf
#uploads to given pomf.se clone

def upload_files(selected_host, file_name, mirror_list):
    url = selected_host
    try:
        answer = requests.post(url, files={'files[]': open(file_name, 'rb')})
        mirror = json.loads(answer.text)
        if not mirror['success']:
            return
        return mirror_list.append(mirror['files'][0]['url'])
    
    except requests.exceptions.ConnectionError:
        return file_name + ' couldn\'t be uploaded to ' + selected_host
    
    except FileNotFoundError:
        return file_name + ' was not found.'        


def upload(file_name):
    file_name = conv_to_mp4(file_name)
    print("Uploading to mirrors...")
    clone_list = json.load(open("host_list.json", 'rb'))
    size = os.path.getsize(file_name)
    save_file_size(file_name)
    print("Size:", str(size/1024/1024) + "MB")
    mirror_list = []
    threads = []
    for clone in clone_list:
        print(str(clone[3]), " ", str(size))
        if clone[3] < size or size > 536870912:
            continue

        t = threading.Thread(target=upload_files, args=(clone[1],file_name,mirror_list))
        threads.append(t)
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print("Upload complete!")
    return mirror_list
        
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
            vid_name
            ]
        conv_process = subprocess.run(ffmpeg_subproc)
        return vid_name

    else:
        return file_name

if __name__ == "__main__":
    if path.exists("/usr/bin/ffmpeg"):
        print(run())
    else:
        print("Needs ffmpeg")
