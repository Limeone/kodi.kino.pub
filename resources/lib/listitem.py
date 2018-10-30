# -*- coding: utf-8 -*-
from xbmcgui import ListItem

from addonutils import get_internal_link
from data import get_adv_setting


class ExtendedListItem(ListItem):

    def __new__(cls, name, label2="", iconImage="", thumbnailImage="", path="", **kwargs):
        return super(ExtendedListItem, cls).__new__(cls, name, label2, iconImage, thumbnailImage,
                                                    path)

    def __init__(self, name, label2="", iconImage="", thumbnailImage="", path="", art=None,
                 info=None, properties=None, addContextMenuItems=False, subtitles=None):
        super(ExtendedListItem, self).__init__(name, label2, iconImage, thumbnailImage, path)
        if info:
            self.setInfos(**info)
            self.setResumeTime(info["video"].get("time"), info["video"].get("duration"))
        if art:
            self.setArt(art)
        if properties:
            self.setProperties(**properties)
        if subtitles:
            self.setSubtitles(subtitles)
        if addContextMenuItems:
            self.addPredefinedContextMenuItems()

    def _addWatchlistContextMenuItem(self, menu_items):
        in_watchlist = self.getProperty("in_watchlist")
        if in_watchlist == "":
            return
        label = u"Не буду смотреть" if int(in_watchlist) else u"Буду смотреть"
        link = get_internal_link(
            "toggle_watchlist",
            id=self.getProperty("id"),
            added=not int(in_watchlist)
        )
        menu_items.append((label, "Container.Update({})".format(link)))

    def _addWatchedContextMenuItem(self, menu_items):
        item_id = self.getProperty("id")
        season_number = self.getVideoInfoTag().getSeason()
        episode_number = self.getVideoInfoTag().getEpisode()
        watched = int(self.getVideoInfoTag().getPlayCount()) > 0
        label = u"Отметить как непросмотренное" if watched else u"Отметить как просмотренное"
        if episode_number != -1 and season_number != -1:
            kwargs = {"id": item_id, "season": season_number, "video": episode_number}
        elif season_number != -1:
            kwargs = {"id": item_id, "season": season_number}
        elif self.getVideoInfoTag().getMediaType() == "tvshow":
            return
        else:
            kwargs = {"id": item_id}
        link = get_internal_link("toggle_watched", **kwargs)
        menu_items.append((label, "Container.Update({})".format(link)))

    def _addBookmarksContextMenuItem(self, menu_items):
        item_id = self.getProperty("id")
        label = u"Изменить закладки"
        link = get_internal_link("edit_bookmarks", item_id=item_id)
        menu_items.append((label, "Container.Update({})".format(link)))

    def addPredefinedContextMenuItems(self, items=None):
        items = items or ["watched", "watchlist", "bookmarks"]
        menu_items = []
        for item in items:
            getattr(self, "_add{}ContextMenuItem".format(item.capitalize()))(menu_items)
        self.addContextMenuItems(menu_items)

    def setProperties(self, **properties):
        for prop, value in properties.items():
            self.setProperty(prop, str(value))

    def setInfos(self, **info):
        for info_type, info_value in info.items():
            self.setInfo(info_type, info_value)

    def setResumeTime(self, resumetime, totaltime):
        if resumetime is None or totaltime is None:
            return
        if (resumetime <= get_adv_setting("video", "ignoresecondsatstart") or
                100 - 100 * resumetime / float(totaltime) <=
                get_adv_setting("video", "ignorepercentatend")):
            self.setProperties(resumetime=0, totaltime=totaltime)
        elif (100 * resumetime / float(totaltime) <=
                get_adv_setting("video", "playcountminimumpercent")):
            self.setProperties(resumetime=resumetime, totaltime=totaltime)
