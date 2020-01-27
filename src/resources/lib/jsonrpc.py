# -*- coding: utf-8 -*-
import json

import xbmc

# https://kodi.wiki/view/JSON-RPC_API/v8


class VideoLibrary(object):
    @classmethod
    def Scan(cls, directory=None):
        if not directory:
            return
        xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "VideoLibrary.Scan",
                    "params": {"directory": directory, "showdialogs": False},
                }
            )
        )

    @classmethod
    def GetTVShows(cls, **kwargs):
        return TVShows(**kwargs)

    @classmethod
    def FindTVShow(cls, title="", year=""):
        query = {"title.is": title, "year.is": year}
        return cls.GetTVShows(where=query, properties=["title"]).first()

    @classmethod
    def GetTVShowDetails(cls, tvshowid, **kwargs):
        return TVShow(tvshowid, **kwargs)

    @classmethod
    def GetMovies(cls, **kwargs):
        return Movies(**kwargs)

    @classmethod
    def FindMovie(cls, title="", year=""):
        query = {"title.is": title, "year.is": year}
        return cls.GetMovies(where=query, properties=["title"]).first()

    @classmethod
    def GetMovieDetails(cls, movieid, **kwargs):
        return Movie(movieid, **kwargs)


class RequestHelper(object):
    def __init__(self):
        self.query = {"jsonrpc": "2.0", "method": "", "params": {}}
        self.response = None

    def __str__(self):
        return json.dumps(self.response) if self.response else None

    def execute(self, query, log=False):
        json_query = xbmc.executeJSONRPC(json.dumps(query))
        try:
            self.response = json.loads(json_query)
        except ValueError:
            self.response = json_query
        return self

    def load(self):
        return self.execute(self.query)

    @property
    def result(self):
        return self.response.get("result") if self.response else None

    @property
    def error(self):
        return self.response.get("error") if self.response else None

    def _collect_filters(self, filters=None):
        if isinstance(filters, dict):
            result = []
            for key, val in filters.items():
                if isinstance(val, int):
                    val = str(val)
                operator = key.split(".")[1]
                field = key.split(".")[0]
                result.append({"operator": operator, "field": field, "value": val})
            return {"and": result}
        else:
            return None

    def _collect_sorting(self, sort=None):
        result = {"order": "ascending", "method": "label", "ignorearticle": True}
        if sort:
            if sort[0] == "-":
                result["order"] = "descending"
                result["method"] = sort[1:-1]
            else:
                result["method"] = sort
        return result

    def _collect_limits(self, start=0, end=None):
        result = {"start": int(start)}
        if end:
            result["end"] = int(end)
        return result


class CollectionHelper(RequestHelper):
    def __init__(self, collection_class, collection_key):
        super(CollectionHelper, self).__init__()
        self.type = None
        self.collection_key = collection_key
        self.collection_class = collection_class

    @property
    def items(self):
        items = self.result.get(self.collection_key) if self.result else None
        return self._build_items(items) if items else None

    def first(self):
        return self.items[0] if self.items else None

    def _build_items(self, items):
        return map(lambda x: self.collection_class(payload=x), items)


class SingleItemHelper(RequestHelper):

    # def __init__(self):
    #   super(SingleItemHelper, self).__init__()

    @property
    def details(self):
        return self.response


class TVShow(SingleItemHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetTVShowDetails",
        "params": {},
        "id": "libTvShows",
    }

    DEFAULT_PROPERTIES = [
        # "cast",
        "episode",
        "episodeguide",
        "genre",
        "imdbnumber",
        "mpaa",
        "originaltitle",
        "premiered",
        "rating",
        "ratings",
        "runtime",
        "season",
        "sorttitle",
        "studio",
        "tag",
        "tvshowid",
        "uniqueid",
        "userrating",
        "votes",
        "watchedepisodes",
        "year",
    ]
    UPDATE_QUERY = {"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": {}}

    REMOVE_QUERY = {"jsonrpc": "2.0", "method": "VideoLibrary.RemoveTVShow", "params": {}}

    def __init__(self, tvshowid=None, properties=None, payload=None):
        if payload:
            self.id = payload["tvshowid"]
            self.response = payload
            self.query = self._build_query(self.id, payload.keys())
        else:
            self.id = tvshowid
            self.response = None
            self.query = self._build_query(self.id, properties)
            self.load()

    def SetDetails(self, **kwargs):
        query = TVShow.UPDATE_QUERY
        query["params"] = kwargs
        query["params"]["tvshowid"] = self.id
        query["id"] = self.id
        return self.execute(query)

    def GetSeasons(self, properties=None):
        return Seasons(self.id, properties=properties)

    def GetEpisodes(self, season_number, properties=None):
        return Episodes(self.id, season_number, properties=properties)

    def GetEpisode(self, season_number, episode, properties=None):
        episodes = self.GetEpisodes(season_number)
        if episodes.items:
            return next(x for x in episodes.items if int(x.details["episode"]) == int(episode))

    def SetEpisodeMarktime(self, season=None, episode=None, marktime=0, total=0):
        episode = self.GetEpisode(season, episode)
        if episode:
            return episode.SetDetails(
                "setResumePoint",
                resume={"position": int(marktime), "total": int(total)},
                runtime=int(marktime),
            )

    def SetEpisodePlaycount(self, season=None, episode=None, playcount=0):
        episode = self.GetEpisode(season, episode)
        if episode:
            return episode.SetDetails("setResumePoint", playcount=int(playcount))

    def Remove(self):
        query = TVShow.REMOVE_QUERY
        query["params"]["tvshowid"] = self.id
        return self.execute(query)

    def _build_query(self, tvshowid, properties):
        query = TVShow.BASE_QUERY
        query["params"]["tvshowid"] = str(tvshowid)
        query["params"]["properties"] = (
            properties if properties is not None else TVShow.DEFAULT_PROPERTIES
        )
        if properties:
            query["params"]["properties"] = properties
        return query


class TVShows(CollectionHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetTVShows",
        "params": {},
        "id": "libTvShows",
    }
    DEFAULT_PROPERTIES = TVShow.DEFAULT_PROPERTIES

    def __init__(self, where=None, properties=None, sort=None, start=0, end=None):
        super(TVShows, self).__init__(TVShow, "tvshows")
        self.query = self._build_query(where, properties, sort, start, end)
        self.load()

    def _build_query(self, where=None, properties=None, sort=None, start=0, end=None):
        query = TVShows.BASE_QUERY
        if where:
            query["params"]["filter"] = self._collect_filters(where)
        query["params"]["properties"] = (
            properties if properties is not None else TVShows.DEFAULT_PROPERTIES
        )
        query["params"]["limits"] = self._collect_limits(start, end)
        query["params"]["sort"] = self._collect_sorting(sort)
        return query


class Season(SingleItemHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetSeasonDetails",
        "params": {},
        "id": "libTvShows",
    }
    DEFAULT_PROPERTIES = [
        "episode",
        "season",
        "seasonid",
        "showtitle",
        "tvshowid",
        "userrating",
        "watchedepisodes",
    ]

    def __init__(self, seasonid=None, properties=None, payload=None):
        if payload:
            self.id = payload["seasonid"]
            self.response = payload
            self.query = self._build_query(self.id, payload.keys())
        else:
            self.id = seasonid
            self.response = None
            self.query = self._build_query(self.id, properties)
            self.load()

    def SetDetails(self, **kwargs):
        query = TVShow.UPDATE_QUERY
        query["params"] = kwargs
        query["params"]["seasonid"] = self.id
        query["id"] = self.id
        return self.execute(query)

    def _build_query(self, seasonid, properties):
        query = Season.BASE_QUERY
        query["params"]["seasonid"] = str(seasonid)
        query["params"]["properties"] = (
            properties if properties is not None else Season.DEFAULT_PROPERTIES
        )
        return query


class Seasons(CollectionHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetSeasons",
        "params": {},
        "id": "libTvShows",
    }

    DEFAULT_PROPERTIES = Season.DEFAULT_PROPERTIES

    def __init__(self, tvshowid, properties=None, sort=None, start=0, end=None):
        super(Seasons, self).__init__(Season, "seasons")
        self.query = self._build_query(tvshowid, properties, sort, start, end)
        self.load()

    def _build_query(self, tvshowid, properties=None, sort=None, start=0, end=None):
        query = Seasons.BASE_QUERY
        query["params"]["tvshowid"] = int(tvshowid)
        query["params"]["properties"] = (
            properties if properties is not None else Season.DEFAULT_PROPERTIES
        )
        query["params"]["limits"] = self._collect_limits(start, end)
        query["params"]["sort"] = self._collect_sorting(sort)
        return query


class Episode(SingleItemHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodeDetails",
        "params": {},
        "id": "libTvShows",
    }
    DEFAULT_PROPERTIES = [
        # "cast",
        "episode",
        "firstaired",
        "originaltitle",
        "productioncode",
        "rating",
        "ratings",
        "season",
        "seasonid",
        "showtitle",
        "specialsortepisode",
        "specialsortseason",
        "tvshowid",
        "uniqueid",
        "userrating",
        "votes",
        "writer",
    ]

    UPDATE_QUERY = {"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {}}

    def __init__(self, episodeid=None, properties=None, payload=None):
        if payload:
            self.id = payload["episodeid"]
            self.response = payload
            self.query = self._build_query(self.id, payload.keys())
        else:
            self.id = episodeid
            self.response = None
            self.query = self._build_query(self.id, properties)
            self.load()

    def _build_query(self, episodeid, properties):
        query = Season.BASE_QUERY
        query["params"]["episodeid"] = episodeid
        query["params"]["properties"] = (
            properties if properties is not None else Episode.DEFAULT_PROPERTIES
        )
        return query

    def SetDetails(self, action, **kwargs):
        query = Episode.UPDATE_QUERY
        query["params"] = kwargs
        query["params"]["episodeid"] = self.id
        query["id"] = action
        return self.execute(query, log=True)


class Episodes(CollectionHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodes",
        "params": {},
        "id": "libTvShows",
    }

    DEFAULT_PROPERTIES = Episode.DEFAULT_PROPERTIES

    def __init__(self, tvshowid, season_number, properties=None, sort=None, start=0, end=None):
        super(Episodes, self).__init__(Episode, "episodes")
        self.query = self._build_query(tvshowid, season_number, properties, sort, start, end)
        self.load()

    def _build_query(self, tvshowid, season_number, properties=None, sort=None, start=0, end=None):
        query = Episodes.BASE_QUERY
        query["params"]["tvshowid"] = int(tvshowid)
        query["params"]["season"] = int(season_number)
        query["params"]["properties"] = (
            properties if properties is not None else Episodes.DEFAULT_PROPERTIES
        )
        query["params"]["limits"] = self._collect_limits(start, end)
        query["params"]["sort"] = self._collect_sorting(sort)
        return query


class Movie(SingleItemHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovieDetails",
        "params": {},
        "id": "libMovies",
    }

    DEFAULT_PROPERTIES = [
        # "cast",
        "country",
        "genre",
        "imdbnumber",
        "movieid",
        "mpaa",
        "originaltitle",
        "plotoutline",
        "premiered",
        "rating",
        "ratings",
        "set",
        "setid",
        "showlink",
        "sorttitle",
        "studio",
        "tag",
        "tagline",
        "top250",
        "trailer",
        "uniqueid",
        "userrating",
        "votes",
        "writer",
        "year",
    ]
    UPDATE_QUERY = {"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {}}

    REMOVE_QUERY = {"jsonrpc": "2.0", "method": "VideoLibrary.RemoveMovie", "params": {}}

    def __init__(self, movieid=None, properties=None, payload=None):
        if payload:
            self.id = payload["movieid"]
            self.response = payload
            self.query = self._build_query(self.id, payload.keys())
        else:
            self.id = movieid
            self.response = None
            self.query = self._build_query(self.id, properties)
            self.load()

    def SetDetails(self, action, **kwargs):
        query = Movie.UPDATE_QUERY
        query["params"] = kwargs
        query["params"]["movieid"] = self.id
        query["id"] = action
        return self.execute(query)

    def SetMovieMarktime(self, marktime=0, total=0):
        return self.SetDetails(
            "setResumePoint",
            resume={"position": int(marktime), "total": int(total)},
            runtime=int(marktime),
        )

    def SetMoviePlaycount(self, playcount=0):
        return self.SetDetails("setResumePoint", playcount=int(playcount))

    def Remove(self):
        query = Movie.REMOVE_QUERY
        query["params"]["movieid"] = self.id
        return self.execute(query)

    def _build_query(self, movieid, properties):
        query = TVShow.BASE_QUERY
        query["params"]["movieid"] = str(movieid)
        query["params"]["properties"] = (
            properties if properties is not None else Movie.DEFAULT_PROPERTIES
        )
        if properties:
            query["params"]["properties"] = properties
        return query


class Movies(CollectionHelper):
    BASE_QUERY = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {},
        "id": "libMovies",
    }
    DEFAULT_PROPERTIES = TVShow.DEFAULT_PROPERTIES

    def __init__(self, where=None, properties=None, sort=None, start=0, end=None):
        super(Movies, self).__init__(Movie, "movies")
        self.query = self._build_query(where, properties, sort, start, end)
        self.load()

    def _build_query(self, where=None, properties=None, sort=None, start=0, end=None):
        query = Movies.BASE_QUERY
        if where:
            query["params"]["filter"] = self._collect_filters(where)
        query["params"]["properties"] = (
            properties if properties is not None else Movies.DEFAULT_PROPERTIES
        )
        query["params"]["limits"] = self._collect_limits(start, end)
        query["params"]["sort"] = self._collect_sorting(sort)
        return query
