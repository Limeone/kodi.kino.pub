# -*- coding: utf-8 -*-
import platform
import re
import sys
import time
import urllib
import urlparse
from functools import wraps

import xbmc
import xbmcgui

from data import __id__, __settings__, __plugin__

__extended_plot__ = __settings__.getSetting('extended_plot')
__ratings_source__ = __settings__.getSetting('ratings_source')


def dict_merge(old, new):
    n = old.copy()
    n.update(new)
    return n


def get_mlink(video, stream_type=None, quality=None, ask_quality="false"):
    """Get media link.

    Args:
        video: a dict from api call
        quality: video quality (480p, 720p, 1080p)
        stream_type: hls, hls2, hls4, http
        ask_quality: "false" or "true"
    """

    def natural_sort(l):
        def convert(text):
            return int(text) if text.isdigit() else text.lower()

        def alphanum_key(key):
            return [convert(c) for c in re.split('([0-9]+)', key)]

        return sorted(l, key=alphanum_key)

    files = {f["quality"]: f["url"] for f in video["files"]}

    # movies trailers come in format: files = {"quality": "url"}
    if isinstance(files.values()[0], basestring):
        files = {"{}p".format(quality): {stream_type: url} for quality, url in files.items()}
        
    flatten_urls_dict = {"{}@{}".format(quality, stream): url for quality, urls in files.items()
                         for stream, url in urls.items()}
    urls_list = natural_sort(flatten_urls_dict.keys())
    if ask_quality == "true":
        dialog = xbmcgui.Dialog()
        result = dialog.select("Выберите качество видео", urls_list)
        if result == -1:
            sys.exit()
        else:
            return flatten_urls_dict[urls_list[result]]
    else:
        try:
            return files[quality][stream_type]
        except KeyError:
            # if there is no such quality then return a link with the highest available quality
            return files[natural_sort(files.keys())[-1]][stream_type]


def build_plot(item):
    # Don't put rating to plot if user don't want to
    if __extended_plot__ == "false":
        return item["plot"]
    final_plot = []
    if item["imdb_rating"]:
        final_plot.append("IMDB: {}".format(str(round(item["imdb_rating"], 1))))
    if item["kinopoisk_rating"]:
        final_plot.append(u"Кинопоиск: {}".format(str(round(item["kinopoisk_rating"], 1))))
    # a new line between the ratings and the plot
    if item["imdb_rating"] or item["kinopoisk_rating"]:
        final_plot.append("")
    final_plot.append(item["plot"])
    return "\n".join(final_plot)


# Take rating from specified resource if this rating exist
def build_rating(item):

    rating = item["imdb_rating"] if __ratings_source__ == 'IMDB' else item["kinopoisk_rating"]

    if __ratings_source__ == "IMDB":
        rating = item["imdb_rating"]
    elif __ratings_source__ == "Kino.Pub":
        rating = item["rating"]
    else:
        rating = item["kinopoisk_rating"]
    
    if rating:
        return float(rating)


# Build path to icon according to it's name
def build_icon_path(name):
    return xbmc.translatePath(
        "special://home/addons/{}/resources/media/{}.png".format(__id__, name)
        )


def get_status(item):
    if item["type"] == "serial" and item["finished"]:
        return u"окончен"
    elif item["type"] == "serial" and not item["finished"]:
        return u"в эфире"
    else:
        return

def build_imdb_number(item):
    if isinstance(item["imdb"], int):
        return "tt{}".format(item["imdb"])
    else:
        return item["imdb"]


def build_titles(item):
    try:
        title, original_title = item['title'].split(" / ")
    except ValueError:
        original_title = title = item['title']
    return title, original_title


def video_info(item, extend=None):
    title, original_title = build_titles(item)
    info = {
        "year": int(item["year"]),
        "genre": ", ".join([x["title"] for x in item["genres"]]),
        "rating": build_rating(item),
        "cast": [x.strip() for x in item["cast"].split(",")],
        "director": item["director"],
        "plot": build_plot(item),
        "title": title,
        "originaltitle": original_title,
        "duration": item.get("duration", {}).get("average"),
        "imdbnumber": build_imdb_number(item),  # string (tt0110293) - IMDb code
        "status": get_status(item),
        "votes": item["rating_votes"],
        "country": ", ".join([x["title"] for x in item["countries"]])
    }
    if extend and isinstance(extend, dict):
        info.update(extend)
    return info


def get_internal_link(path, **params):
    """Form internal link for plugin navigation"""
    return urlparse.urlunsplit(("plugin", __id__, path, urllib.urlencode(params), ""))


def nav_internal_link(action, **params):
    xbmc.executebuiltin("Container.Update({})".format(get_internal_link(action, **params)))


def notice(message, heading="", time=4000):
    xbmc.executebuiltin('XBMC.Notification("{}", "{}", "{}")'.format(heading, message, time))


def trailer_link(item):
    if item.get("trailer"):
        trailer = item["trailer"]
        return get_internal_link("trailer", id=item["id"], sid=trailer["id"])
    return None


def update_device_info(force=False):
    from client import KinoPubClient
    # Update device info
    deviceInfoUpdate = __settings__.getSetting("device_info_update")
    if force or not deviceInfoUpdate or int(deviceInfoUpdate) + 1800 < int(time.time()):
        result = {"build_version": "Busy", "friendly_name": "Busy"}
        while "Busy" in result.values():
            result = {
                "build_version": xbmc.getInfoLabel("System.BuildVersion"),
                "friendly_name": xbmc.getInfoLabel("System.FriendlyName")
            }
        software = "Kodi {}".format(result["build_version"].split()[0])
        KinoPubClient("device/notify").post(data={
            "title": result["friendly_name"],
            "hardware": platform.machine(),
            "software": software
        })
        __settings__.setSetting("device_info_update", str(int(float(time.time()))))


class Request(object):

    @property
    def handle(self):
        return int(sys.argv[1])

    @property
    def path(self):
        return sys.argv[0].replace(__plugin__, "")

    @property
    def args(self):
        return dict(urlparse.parse_qsl(sys.argv[2].lstrip("?")))


request = Request()

ROUTES = dict()


def route(path):
    def decorator_route(f):
        ROUTES[path] = f

        @wraps(f)
        def wrapper_route(*args, **kwargs):
            xbmc.log("{} : {}. {}".format(__plugin__, f.__name__, str(request.args)))
            return f(*args, **kwargs)
        return wrapper_route
    return decorator_route
