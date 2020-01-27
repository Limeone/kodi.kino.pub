# -*- coding: utf-8 -*-
import json
import os

import xbmcvfs

from resources.lib.jsonrpc import VideoLibrary
from resources.lib.plugin import Plugin

plugin = Plugin()


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
    def sync_sections(cls):
        cls._check_paths()
        for section, shortcuts in cls._syncable_sections().items():
            for shortcut in shortcuts:
                response = plugin.client("items/{}".format(shortcut)).get(data={"type": section})
                items = response["items"]
                for item in items:
                    cls.add(item, force_library_scan=False)
        VideoLibrary.Scan(cls.DUMP_DIR)

    @classmethod
    def add(cls, info, force_library_scan=True):
        if cls._is_movie(info):
            item = Movie(info)
        elif cls._is_movie_set(info):
            item = MovieSet(info)
        else:
            item = TVShow(info)
        # anime... skip it when possible
        if item.is_anime and cls.SKIP_ANIME and not force_library_scan:
            return
        # do not fetch already saved and manually blocked items
        if not item.is_synced and not item.is_blocked:
            # items fetched with batch do not have enougth info
            if not force_library_scan:
                item.fetchExtendedInfo()

            item.sync()
        # Do not start library scan if it is not manually triggered
        if force_library_scan:
            VideoLibrary.Scan(cls.DUMP_DIR)

    @classmethod
    def remove(cls, info):
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
            "set": {
                "dirname": "{title} ({year}) ({episodename})",
                "nfo": "{dirname}.nfo",
                "strm": "{dirname}.strm",
            },
        },
    }

    def __init__(self, info, _type):
        self.naming = Base.NAMING_CONVENTION[_type]
        self.type = _type
        self.info = info
        if not xbmcvfs.exists("{}/".format(self.path)):
            xbmcvfs.mkdirs(self.path)

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
        self.saveNFO()
        self.saveSTRM()
        AddonLibrary.save(
            self.id,
            updated_at=self.info["updated_at"],
            blocked=False,
            videos=[{"title": self.title, "year": self.year}],
        )

    def disable_sync(self):
        AddonLibrary.save(self.id, blocked=True)

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
        movie_info = {"updated_at": self.info["updated_at"], "blocked": False, "videos": []}
        for episode_info in self.info["videos"]:
            episode = MovieSetEpisode(self, episode_info)
            episode.sync()
            movie_info["videos"].append({"title": episode.episodetitle, "year": self.year})

        AddonLibrary.save(self.id, **movie_info)


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

    def disable_sync(self):
        AddonLibrary.save(self.id, blocked=True)
        tvshow = VideoLibrary.FindTVShow(title=self.title, year=self.year)
        if tvshow:
            tvshow.Remove()
        os.remove(self.path)

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
