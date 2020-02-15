# -*- coding: utf-8 -*-
import json
import os
import shutil
from datetime import datetime

import xbmcvfs

from resources.lib.jsonrpc import VideoLibrary
from resources.lib.plugin import Plugin

plugin = Plugin()


def updated_days_ago(updated_at):
    # for backword compatibility
    if updated_at is None:
        return 0

    delta = datetime.now() - datetime.fromtimestamp(int(updated_at))
    return delta.days


class AddonLibrary(object):

    DUMP_DIR = os.path.join(plugin.settings.folder, "KinoPub")
    DUMP_PATH = os.path.join(DUMP_DIR, "kinopubdump")
    ENABLED = bool(plugin.settings.sync_enabled and plugin.settings.folder)
    SKIP_ANIME = plugin.settings.skip_anime

    @classmethod
    def find(cls, item_id):
        dump = cls._getDump()
        if not dump:
            return
        return dump.get(str(item_id))

    @classmethod
    def save(cls, item_id, **attrs):
        dump = cls._getDump()
        if not dump:
            dump = {}
        item_attrs = dump.get(str(item_id))
        if not item_attrs:
            item_attrs = {}
        for key, val in attrs.items():
            item_attrs[key] = val
        dump[str(item_id)] = item_attrs
        cls._saveDump(dump)

    @classmethod
    def drop(cls, item_id):
        dump = cls._getDump()
        if not dump:
            return
        item_attrs = dump.get(str(item_id))
        if not item_attrs:
            return
        del dump[str(item_id)]
        cls._saveDump(dump)

    @classmethod
    def cleanup(cls):
        if os.path.isdir(cls.DUMP_DIR):
            shutil.rmtree(cls.DUMP_DIR)
        VideoLibrary.Clean()

    @classmethod
    def SyncSectionsToVideoLibray(cls):
        cls._check_paths()
        synced_ids = []
        for section, shortcuts in cls._syncable_sections().items():
            for shortcut in shortcuts:
                response = plugin.client("items/{}".format(shortcut)).get(data={"type": section})
                for item in response["items"]:
                    # do not double sync items that are both hot and popular
                    if item["id"] in synced_ids:
                        continue
                    # do not update unnecessary and
                    cls.SyncItem(item, force=False)
                    synced_ids.append(item["id"])

        # sync subscribed serials
        subscribed_tvshows = plugin.client("watching/serials").get(data={"subscribed": 1})
        for item in subscribed_tvshows["items"]:
            # do not double sync items that are both hot and popular
            if item["id"] in synced_ids:
                continue
            item = plugin.client("items/{}".format(item["id"])).get()["item"]
            # do not update unnecessary and
            cls.SyncItem(item, force=True)
            synced_ids.append(item["id"])
        return synced_ids

    # Media may be exluded from popular or hot, but still should be updated
    @classmethod
    def UpdateSavedMedia(cls, exclude=[]):
        dump = cls._getDump()
        for key, item in dump.items():
            # skip manually blocked media
            if item["blocked"]:
                continue
            # skip items updated more than 10 days ago, most likely
            # it won't be updated anymore
            if updated_days_ago(item.get("updated_at", None)) > 10:
                continue
            # skip excluded items
            if int(key) in exclude:
                continue
            # fetch fresh media info
            info = plugin.client("items/{}".format(key)).get()["item"]
            # force update saved item
            cls.SyncItem(info, force=True)

    @classmethod
    def ScanVideoLibrary(cls):
        VideoLibrary.Scan(cls.DUMP_DIR)

    @classmethod
    def SyncItem(cls, info, force=False):
        if cls._is_movie(info):
            item = Movie(info)
        elif cls._is_movie_set(info):
            item = MovieSet(info)
        else:
            item = TVShow(info)

        # anime... skip it when possible
        if item.is_anime and cls.SKIP_ANIME and not force:
            return
        # skip saved and not changed media
        if item.is_synced and not force:
            return
        # skip saved and manually blocked media
        if item.is_blocked and not force:
            return

        item.sync()

    @classmethod
    def DisableItem(cls, info):
        if cls._is_movie(info):
            item = Movie(info)
        elif cls._is_movie_set(info):
            item = MovieSet(info)
        else:
            item = TVShow(info)
        item.disable_sync()

    @classmethod
    def _check_paths(cls):
        if not os.path.exists(cls.DUMP_PATH):
            xbmcvfs.mkdirs(cls.DUMP_DIR)

    @classmethod
    def _getDump(cls):
        if not os.path.exists(cls.DUMP_PATH):
            return
        dumpfile = xbmcvfs.File(cls.DUMP_PATH, "r")
        try:
            dump = json.loads(dumpfile.read())
        except ValueError:
            dump = None
        dumpfile.close()
        return dump

    @classmethod
    def _saveDump(cls, dump):
        cls._check_paths()
        dumpfile = xbmcvfs.File(cls.DUMP_PATH, "w+")
        dumpfile.write(json.dumps(dump))
        dumpfile.close()

    @classmethod
    def _syncable_sections(cls):
        sections = {"movie": [], "serial": []}
        if plugin.settings.save_hot_movie:
            sections["movie"].append("hot")
        if plugin.settings.save_popular_movie:
            sections["movie"].append("popular")
        if plugin.settings.save_hot_serial:
            sections["serial"].append("hot")
        if plugin.settings.save_popular_serial:
            sections["serial"].append("popular")
        return sections

    @classmethod
    def _is_movie(cls, info):
        return not cls._is_tvshow(info) and not info["subtype"]

    @classmethod
    def _is_movie_set(cls, info):
        return not cls._is_tvshow(info) and info["subtype"]

    @classmethod
    def _is_tvshow(cls, info):
        return info["type"] in ["serial", "docuserial", "tvshow"]


class Base(object):
    NAMING_CONVENTION = {
        "tvshow": {
            "parentdir": "Сериалы",
            "nfo": "tvshow.nfo",
            "dirname": "{title} ({year})",
            "episode": {
                "nfo": "{dirname} S{season_number:02d}E{episode_number:02d}.nfo",
                "strm": "{dirname} S{season_number:02d}E{episode_number:02d}.strm",
            },
        },
        "movie": {
            "parentdir": "Фильмы",
            "nfo": "{dirname}.nfo",
            "dirname": "{title} ({year})",
            "strm": "{dirname}.strm",
            "set": {"nfo": "{dirname}.nfo", "strm": "{dirname}.strm"},
        },
    }

    def __init__(self, info, _type):
        self.naming = Base.NAMING_CONVENTION[_type]
        self.type = _type
        self.info = info
        self._init_path()

    def _init_path(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    @property
    def dirname(self):
        return self.naming["dirname"].format(title=self.title, year=self.year)

    @property
    def path(self):
        return os.path.join(AddonLibrary.DUMP_DIR, self.naming["parentdir"], self.dirname)

    @property
    def imdb(self):
        return self.info["imdb"]

    @property
    def id(self):
        return self.info["id"]

    @property
    def title(self):
        return self.info["title"].encode("utf8").split("/")[0].rstrip()

    def titleNFO(self):
        return "<title>{}<title>".format(self.title)

    @property
    def originaltitle(self):
        titles = self.info["title"].encode("utf8").split("/")
        try:
            return titles[1].lstrip()
        except IndexError:
            return titles[0].rstrip()

    def originaltitleNFO(self):
        return "<originaltitle>{}<originaltitle>".format(self.originaltitle)

    @property
    def year(self):
        return self.info["year"]

    def yearNFO(self):
        return "<year>{}</year>".format(self.year)

    @property
    def poster(self):
        return self.info["posters"].get("big", "")

    def posterNFO(self):
        return '<thumb aspect="poster">{poster}</thumb>'.format(poster=self.poster)

    @property
    def fanart(self):
        return self.info["posters"].get("wide", "")

    def fanartNFO(self):
        return "<fanart><thumb>{fanart}</thumb><fanart>".format(fanart=self.fanart)

    @property
    def is_synced(self):
        item = AddonLibrary.find(self.id)
        if item:
            return False if int(self.info["updated_at"]) > int(item["updated_at"]) else True
        else:
            return False

    @property
    def is_blocked(self):
        item = AddonLibrary.find(self.id)
        return item["blocked"] if item else False

    @property
    def is_anime(self):
        return "Аниме" in self.genre

    @property
    def cast(self):
        return self.info["cast"].split(", ")

    def castNFO(self):
        r = [
            "<actor><name>{}</name><order>{}</order></actor>".format(a.encode("utf8"), i)
            for i, a in enumerate(self.cast, 0)
        ]
        return "".join(r)

    @property
    def plot(self):
        return self.info["plot"].encode("utf8")

    def plotNFO(self):
        return "<plot>{}</plot>".format(self.plot)

    @property
    def genre(self):
        return [i["title"].encode("utf8") for i in self.info["genres"]]

    def genreNFO(self):
        r = ["<genre>{}</genre>".format(i) for i in self.genre]
        return r.join()

    @property
    def scrapper_link(self):
        return "http://www.imdb.com/title/tt{}/".format(self.imdb) if self.imdb else ""

    @property
    def insufficient_info(self):
        return self.info.get("seasons", None) is None

    def fetchExtendedInfo(self):
        self.info = plugin.client("items/{}".format(self.id)).get()["item"]

    def genNFOXML(self, *attrs):
        xml_str = "<?xml version='1.0' encoding='utf8'?>"
        xml_str += "<{}>".format(self.type)
        for attr in attrs:
            xml_str += attr
        xml_str += "<tag>kino.pub</tag>"
        xml_str += "</{}>".format(self.type)
        xml_str += self.scrapper_link
        return xml_str

    def _save_to_file(self, filename, text):
        f = xbmcvfs.File(os.path.join(self.path, filename), "w+")
        f.write(str(text))
        f.close()


class Movie(Base):
    def __init__(self, info):
        super(Movie, self).__init__(info, "movie")

    def sync(self):
        # New movied could be added as multi movies with different translations
        # eventually these items merge to single movie with several audio
        # Such media should be removed from library and synced again
        saved_item = AddonLibrary.find(self.id)
        if saved_item:
            if saved_item.get("multi", False):
                movie_set = MovieSet(self.info)
                movie_set.destroy()
                self._init_path()
        if self.insufficient_info:
            self.fetchExtendedInfo()
        self.saveNFO()
        self.saveSTRM()
        AddonLibrary.save(
            self.id,
            updated_at=self.info["updated_at"],
            blocked=False,
            multi=False,
            videos=[{"title": self.title, "year": self.year}],
        )

    def disable_sync(self, blocked=True):
        AddonLibrary.save(self.id, blocked=blocked)
        movie = VideoLibrary.FindMovie(title=self.title, year=self.year)
        if movie:
            movie.Remove()
        shutil.rmtree(self.path)

    @property
    def insufficient_info(self):
        return self.info.get("videos", None) is None

    def saveSTRM(self):
        url = plugin.routing.build_url("play", self.info["id"], 1, local=True)
        filename = self.naming["strm"].format(dirname=self.dirname)
        self._save_to_file(filename, str(url))

    @property
    def playcount(self):
        return self.info["videos"][0]["watched"]

    def playcountNFO(self):
        return "<playcount>{}</playcount>".format(self.playcount)

    @property
    def watchingposition(self):
        return self.info["videos"][0]["watching"]["time"]

    @property
    def duration(self):
        return self.info["videos"][0]["duration"]

    def resumeNFO(self):
        return "<resume><position>{}</position><total>{}</total></resume>".format(
            self.watchingposition, self.duration
        )

    def genNFOXML(self):
        return super(Movie, self).genNFOXML(
            self.titleNFO(),
            self.yearNFO(),
            self.plotNFO(),
            self.originaltitleNFO(),
            self.castNFO(),
            self.playcountNFO(),
            self.resumeNFO(),
            self.posterNFO(),
            self.fanartNFO(),
        )

    def saveNFO(self):
        nfo = self.genNFOXML()
        filename = self.naming["nfo"].format(dirname=self.dirname)
        self._save_to_file(filename, nfo)


class MovieSet(Base):
    def __init__(self, info):
        super(MovieSet, self).__init__(info, "movie")

    def sync(self):
        movie_info = {
            "updated_at": self.info["updated_at"],
            "blocked": False,
            "multi": True,
            "videos": [],
        }

        if self.insufficient_info:
            self.fetchExtendedInfo()
        for episode_info in self.info["videos"]:
            episode = MovieSetEpisode(self, episode_info)
            episode.sync()
            movie_info["videos"].append({"title": episode.episodetitle, "year": self.year})

        AddonLibrary.save(self.id, **movie_info)

    def disable_sync(self, block=True):
        dump_info = AddonLibrary.find(self.id)
        for episode_info in dump_info["videos"]:
            # episode = MovieSetEpisode(self, episode_info)
            movie = VideoLibrary.FindMovie(title=episode_info["title"], year=episode_info["year"])
            if movie:
                movie.Remove()
        shutil.rmtree(self.path)
        # there are cases when initially movies are added to library as multi files
        # with different translations, after some time this movie merged to single file
        # with different audio streams
        if block:
            # remove item from library and never sync until manually triggered
            AddonLibrary.save(self.id, blocked=True)
        else:
            # remove from dump if same item_id should be resynced
            AddonLibrary.drop(self.id)

    @property
    def insufficient_info(self):
        return self.info.get("videos", None) is None

    def destroy(self):
        self.disable_sync(block=False)


class MovieSetEpisode(Base):
    def __init__(self, movie, episode_info):
        self.episode_info = episode_info
        self.movie = movie
        super(MovieSetEpisode, self).__init__(movie.info, "movie")

    @property
    def path(self):
        return os.path.join(self.movie.path, self.dirname)

    @property
    def dirname(self):
        return self.episodename

    @property
    def episodename(self):
        return self.episode_info["title"].encode("utf8")

    @property
    def episodetitle(self):
        return "{} ({})".format(self.title, self.episodename)

    @property
    def episodenumber(self):
        return self.episode_info["number"]

    def titleNFO(self):
        return "<title>{}<title>".format(self.episodetitle)

    @property
    def movie_set(self):
        return self.title

    def setNFO(self):
        return "<set><name>{}</name></set>".format(self.movie_set)

    @property
    def playcount(self):
        return self.episode_info["watched"]

    def playcountNFO(self):
        return "<playcount>{}</playcount>".format(self.playcount)

    @property
    def watchingposition(self):
        return self.episode_info["watching"]["time"]

    @property
    def duration(self):
        return self.episode_info["duration"]

    def resumeNFO(self):
        return "<resume><position>{}</position><total>{}</total></resume>".format(
            self.watchingposition, self.duration
        )

    @property
    def poster(self):
        return self.movie.info["posters"].get("big", "")

    def posterNFO(self):
        return '<thumb aspect="poster">{poster}</thumb>'.format(poster=self.poster)

    @property
    def fanart(self):
        return self.movie.info["posters"].get("wide", "")

    def fanartNFO(self):
        return "<fanart><thumb>{fanart}</thumb><fanart>".format(fanart=self.fanart)

    def sync(self):
        self.saveSTRM()
        self.saveNFO()

    def saveSTRM(self):
        url = plugin.routing.build_url("play", self.id, self.episodenumber, local=True, multi=True)
        filename = self.naming["set"]["strm"].format(dirname=self.dirname)
        self._save_to_file(filename, str(url))

    def genNFOXML(self):
        return super(MovieSetEpisode, self).genNFOXML(
            self.titleNFO(),
            self.yearNFO(),
            self.plotNFO(),
            self.originaltitleNFO(),
            self.castNFO(),
            self.playcountNFO(),
            self.resumeNFO(),
            self.posterNFO(),
            self.fanartNFO(),
        )

    def saveNFO(self):
        nfo = self.genNFOXML()
        filename = self.naming["set"]["nfo"].format(dirname=self.dirname)
        self._save_to_file(filename, nfo)


class TVShow(Base):
    def __init__(self, info):
        super(TVShow, self).__init__(info, "tvshow")

    def sync(self):
        if self.insufficient_info:
            self.fetchExtendedInfo()
        self.saveNFO()
        self.save_episodes()
        AddonLibrary.save(
            self.info["id"],
            title=self.title,
            year=self.info["year"],
            updated_at=self.info["updated_at"],
            blocked=False,
        )

    def genNFOXML(self):
        return super(TVShow, self).genNFOXML(
            self.titleNFO(),
            self.yearNFO(),
            self.plotNFO(),
            self.originaltitleNFO(),
            self.castNFO(),
            self.posterNFO(),
            self.fanartNFO(),
        )

    def saveNFO(self):
        nfo = self.genNFOXML()
        filename = self.naming["nfo"]
        self._save_to_file(filename, nfo)

    def disable_sync(self, blocked=True):
        AddonLibrary.save(self.id, blocked=blocked)
        tvshow = VideoLibrary.FindTVShow(title=self.title, year=self.year)
        if tvshow:
            tvshow.Remove()
        shutil.rmtree(self.path)

    @property
    def insufficient_info(self):
        return self.info.get("seasons", None) is None

    def save_episodes(self):
        for season in self.info["seasons"]:
            for episode in season["episodes"]:
                self._save_episode_nfo(season, episode)
                self._save_episode_strm(season, episode)

    def _save_episode_nfo(self, season, episode):
        text = (
            "<?xml version='1.0' encoding='utf8'?>"
            + "<episodedetails>"
            + "<playcount>{}</playcount>".format(episode["watched"])
            + "<resume>"
            + "<position>{}</position>".format(episode["watching"]["time"])
            + "<total>{}</total>".format(episode["duration"])
            + "</resume>"
            + "</episodedetails>"
            + self.scrapper_link
        )

        filename = self.naming["episode"]["nfo"].format(
            dirname=self.dirname, season_number=season["number"], episode_number=episode["number"]
        )
        self._save_to_file(filename, text)

    def _save_episode_strm(self, season, episode):
        filename = self.naming["episode"]["strm"].format(
            dirname=self.dirname, season_number=season["number"], episode_number=episode["number"]
        )
        url = plugin.routing.build_url(
            "play", self.id, episode["number"], local=True, season=season["number"]
        )
        self._save_to_file(filename, url)
