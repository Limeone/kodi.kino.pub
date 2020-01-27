# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import time

import xbmc
import xbmcgui

from resources.lib.addon_library import AddonLibrary
from resources.lib.jsonrpc import VideoLibrary


class Player(xbmc.Player):
    def __init__(self, list_item):
        self.plugin = list_item.plugin
        self.list_item = list_item
        self.is_playing = True
        self.marktime = 0
        self.play_duration = 0

    def set_marktime(self):
        if self.isPlaying():
            self.marktime = int(self.getTime())

    @property
    def should_make_resume_point(self):
        # https://kodi.wiki/view/HOW-TO:Modify_automatic_watch_and_resume_points#Settings_explained
        return (
            self.marktime > self.plugin.settings.advanced("video", "ignoresecondsatstart")
            and not self.should_mark_as_watched
        )

    @property
    def should_mark_as_watched(self):
        return 100 * self.marktime / float(
            self.list_item.getProperty("play_duration")
        ) > self.plugin.settings.advanced("video", "playcountminimumpercent")

    @property
    def should_reset_resume_point(self):
        return self.marktime < self.plugin.settings.advanced("video", "ignoresecondsatstart") and (
            float(self.list_item.getProperty("play_resumetime"))
            > self.plugin.settings.advanced("video", "ignoresecondsatstart")
        )

    @property
    def should_refresh_token(self):
        return int(time.time()) + int(self.list_item.getProperty("play_duration")) >= int(
            self.plugin.settings.access_token_expire
        )

    @property
    def _base_data(self):
        item_id = self.list_item.getProperty("item_id")
        video_number = self.list_item.getProperty("video_number")
        season_number = self.list_item.getProperty("season_number")
        if season_number:
            data = {"id": item_id, "season": season_number, "video": video_number}
        else:
            data = {"id": item_id, "video": video_number}
        return data

    def updateLocalMarktime(self, data=None):
        if not AddonLibrary.ENABLED:
            return
        item = AddonLibrary.find(data["id"])
        video_number = int(data["video"])
        if item:
            self.plugin.logger.notice("setting local resume point")
        resp = None
        if data.get("season") and item:
            tvshow = VideoLibrary.FindTVShow(title=item["title"], year=item["year"])
            if tvshow:
                resp = tvshow.SetEpisodeMarktime(
                    season=data["season"],
                    episode=data["video"],
                    marktime=data["time"],
                    total=self.play_duration,
                )
        elif item:
            title = item["videos"][video_number - 1]["title"]
            year = item["videos"][video_number - 1]["year"]
            movie = VideoLibrary.FindMovie(title=title, year=year)
            if movie:
                resp = movie.SetMovieMarktime(marktime=data["time"], total=self.play_duration)
        self.plugin.logger.notice(resp)

    def updateLocalPlaycount(self, data=None):
        if not AddonLibrary.ENABLED:
            return
        item = AddonLibrary.find(data["id"])
        video_number = int(data["video"])
        if item:
            self.plugin.logger.notice("setting local as watched")
        resp = None
        if data.get("season") and item:
            tvshow = VideoLibrary.FindTVShow(title=item["title"], year=item["year"])
            if tvshow:
                tvshow.SetEpisodePlaycount(
                    season=data["season"], episode=data["video"], playcount=1
                )
        elif item:
            title = item["videos"][video_number - 1]["title"]
            year = item["videos"][video_number - 1]["year"]
            movie = VideoLibrary.FindMovie(title=title, year=year)
            if movie:
                resp = movie.SetMoviePlaycount(playcount=1)
        self.plugin.logger.notice(resp)

    def onPlayBackStarted(self):
        self.plugin.logger.notice("playback started")
        # https://github.com/trakt/script.trakt/wiki/Providing-id's-to-facilitate-scrobbling
        # imdb id should be 7 digits with leading zeroes with tt prepended
        imdb_id = "tt{:07d}".format(int(self.list_item.getProperty("imdbnumber")))
        ids = json.dumps({"imdb": imdb_id})
        xbmcgui.Window(10000).setProperty("script.trakt.ids", ids)
        self.play_duration = self.list_item.getProperty("play_duration")
        if self.should_refresh_token:
            self.plugin.logger.notice("access token should be refreshed")
            self.plugin.auth.get_token()

    def onPlayBackStopped(self):
        self.is_playing = False
        data = self._base_data
        self.plugin.logger.notice("playback stopped")
        if self.should_make_resume_point:
            data["time"] = self.marktime
            self.plugin.logger.notice("sending resume point")
            self.plugin.client("watching/marktime").get(data=data)
            self.updateLocalMarktime(data=data)
        elif self.should_mark_as_watched and int(self.list_item.getProperty("playcount")) < 1:
            data["status"] = 1
            self.plugin.logger.notice("marking as watched")
            self.plugin.client("watching/toggle").get(data=data)
            self.updateLocalPlaycount(data=data)
        elif self.should_reset_resume_point:
            data["time"] = 0
            self.plugin.logger.notice("resetting resume point")
            self.plugin.client("watching/marktime").get(data=data)
            self.updateLocalMarktime(data=data)
        else:
            return

    def onPlayBackEnded(self):
        self.is_playing = False
        self.plugin.logger.notice("playback ended")
        if int(self.list_item.getProperty("playcount")) < 1:
            data = self._base_data
            data["status"] = 1
            self.plugin.logger.notice("marking as watched")
            self.plugin.client("watching/toggle").get(data=data)
            self.updateLocalPlaycount(data=data)

    def onPlaybackError(self):
        self.plugin.logger.error("playback error")
        self.is_playing = False
