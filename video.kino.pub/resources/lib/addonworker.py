#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, urllib2, urlparse
import sys
import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import json
import addonutils
import time

__id__ = 'video.kino.pub'
__addon__ = xbmcaddon.Addon(id=__id__)
__settings__ = xbmcaddon.Addon(id=__id__)
__skinsdir__ = "DefaultSkin"
__language__ = __addon__.getLocalizedString
__plugin__ = "plugin://%s" % __id__

DEFAULT_QUALITY = __settings__.getSetting("video_quality")
DEFAULT_STREAM_TYPE = __settings__.getSetting("stream_type")

_ADDON_PATH =   xbmc.translatePath(__addon__.getAddonInfo('path'))
if (sys.platform == 'win32') or (sys.platform == 'win64'):
    _ADDON_PATH = _ADDON_PATH.decode('utf-8')
handle = int(sys.argv[1])
xbmcplugin.setContent(handle, 'movie')


import authwindow as auth
Auth = auth.Auth(__settings__)
def api(action, params={}, url="http://api.service-kp.com/v1", timeout=600):
    access_token = __settings__.getSetting('access_token')
    xbmc.log("Access token is: %s" % access_token)
    if access_token:
        params['access_token'] = access_token
    params = urllib.urlencode(params)
    xbmc.log("%s/%s?%s" % (url, action, params))
    try:
        access_token_expire = __settings__.getSetting('access_token_expire')
        if int(access_token_expire) - int(time.time()) <= 15 * 60:
            # try to refresh token
            status, resp = Auth.get_token(refresh=True)
            if status != Auth.SUCCESS:
                nav_internal_link()

        response = urllib2.urlopen("%s/%s?%s" % (url, action, params), timeout=timeout)
        data = json.loads(response.read())
        return data
    except urllib2.HTTPError as e:
        data = json.loads(e.read())
        return data
    except Exception as e:
        print e
        return {
            'status': 105,
            'name': 'Name Not Resolved',
            'message': 'Name not resolved',
            'code': 0
        }

# Show pagination
def show_pagination(pagination, action, qp):
    # Add "next page" button
    if (int(pagination['current'])) + 1 <= int(pagination['total']):
        qp['page'] = int(pagination['current'])+1
        li = xbmcgui.ListItem("[COLOR FFFFF000]Вперёд[/COLOR]")
        link = get_internal_link(action, qp)
        xbmcplugin.addDirectoryItem(handle, link, li, True)
    xbmcplugin.endOfDirectory(handle)

# Fill directory for items
def show_items(items):
    xbmc.log("%s : show_items. Total items: %s" % (__plugin__, str(len(items))))
    # Fill list with items
    for item in items:
        isdir = True if item['type'] in ['serial', 'docuserial'] else False
        link = get_internal_link('view', {'id': item['id']})
        li = xbmcgui.ListItem(item['title'].encode('utf-8'), iconImage=item['posters']['big'], thumbnailImage=item['posters']['big'])
        li.setInfo('Video', addonutils.video_info(item))
        # If not serials or multiseries movie, create playable item
        if item['type'] not in ['serial', 'docuserial']:
            if item['subtype'] == '':
                link = get_internal_link('play', {'id': item['id'], 'video': 1})
                #li.setInfo('Video', {'playcount': int(full_item['videos'][0]['watched'])})
                li.setProperty('IsPlayable', 'true')
                isdir = False
            else:
                link = get_internal_link('view', {'id': item['id']})
                isdir = True
        xbmcplugin.addDirectoryItem(handle, link, li, isdir)

# qp - dict, query paramters
# fmt - show format
#  s - show search
#  l - show last
#  p - show popular
#  s - show alphabet sorting
#  g - show genres folder
def add_default_headings(qp, fmt="slp"):
    if 's' in fmt:
        li = xbmcgui.ListItem('[COLOR FFFFF000]Поиск[/COLOR]')
        xbmcplugin.addDirectoryItem(handle, get_internal_link('search', qp), li, False)
    if 'l' in fmt:
        li = xbmcgui.ListItem('[COLOR FFFFF000]Последние[/COLOR]')
        xbmcplugin.addDirectoryItem(handle, get_internal_link('items', qp), li, True)
    if 'p' in fmt:
        li = xbmcgui.ListItem('[COLOR FFFFF000]Популярные[/COLOR]')
        xbmcplugin.addDirectoryItem(handle, get_internal_link('items', addonutils.dict_merge(qp, {'sort': '-rating'})), li, True)
    if 'a' in fmt:
        li = xbmcgui.ListItem('[COLOR FFFFF000]По алфавиту[/COLOR]')
        xbmcplugin.addDirectoryItem(handle, get_internal_link('alphabet', qp), li, True)
    if 'g' in fmt:
        li = xbmcgui.ListItem('[COLOR FFFFF000]Жанры[/COLOR]')
        xbmcplugin.addDirectoryItem(handle, get_internal_link('genres', qp), li, True)


# Form internal link for plugin navigation
def get_internal_link(action, params={}):
    global __plugin__
    params = urllib.urlencode(params)
    return "%s/%s?%s" % (__plugin__, action, params)

def nav_internal_link(action, params={}):
    ret = xbmc.executebuiltin('Container.Update(%s)' % get_internal_link(action, params))

def notice(message, heading, time=4000):
    xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s")' % (heading, message, time))

def route(fakeSys=None):
    global __plugin__

    if  fakeSys:
        current = fakeSys.split('?')[0]
        qs = fakeSys.split('?')['?' in fakeSys]
    else:
        current = sys.argv[0]
        qs = sys.argv[2]
    action = current.replace(__plugin__, '').lstrip('/')
    action = action if action else 'login'
    actionFn = 'action' + action.title()
    qp = get_params(qs)

    xbmc.log("%s : route. %s" % (__plugin__, str(qp)))
    globals()[actionFn](qp)


# Parse query string params into dict
def get_params(qs):
    params = {}
    if qs:
        qs = qs.replace('?', '').split('/')[-1]
        for i in qs.split('&'):
            if '=' in i:
                k,v = i.split('=')
                params[k] = urllib.unquote_plus(v)
    return params



# Entry point
def init():
    route()

"""
 Actions
"""

def actionLogin(qp):
    xbmc.log("%s : actionLogin. %s" % (__plugin__, str(qp)))

    access_token = __settings__.getSetting('access_token')
    device_code = __settings__.getSetting('device_code')
    access_token_expire = __settings__.getSetting('access_token_expire')

    def showActivationWindow():
        xbmc.log("%s : actionLogin - No acess_token. Show modal auth" % __plugin__)
        wn = auth.AuthWindow("auth.xml", _ADDON_PATH, __skinsdir__, settings=__settings__)
        wn.doModal()
        del wn
        xbmc.log("%s : actionLogin - Close modal auth" % __plugin__)

    # if no access_token exists
    if not access_token:
        showActivationWindow()
        nav_internal_link('login')
        return
    else:
        if int(access_token_expire) - int(time.time()) <= 15 * 60:
            # try to refresh token
            status, resp = Auth.get_token(refresh=True)

        # test API call
        response = api('types')
        if int(response['status']) == 401:
            status, resp = Auth.get_token(refresh=True)
            if status != Auth.SUCCESS:
                # reset access_token
                Auth.settings.setSetting('access_token', '')
                showActivationWindow()
                nav_internal_link('login')

        nav_internal_link('index')

# Main screen - show type list
def actionIndex(qp):
    xbmc.log("%s : actionIndex. %s" % (__plugin__, str(qp)))
    xbmc.executebuiltin('Container.SetViewMode(0)')
    if 'type' in qp:
        add_default_headings(qp, "slpga")
    else:
        response = api('types')
        if response['status'] == 200:
            add_default_headings(qp)
            # Add bookmarks
            li = xbmcgui.ListItem('[COLOR FFFFF000]Закладки[/COLOR]')
            xbmcplugin.addDirectoryItem(handle, get_internal_link('bookmarks'), li, True)
            for i in response['items']:
                li = xbmcgui.ListItem(i['title'].encode('utf-8'))
                #link = get_internal_link('items', {'type': i['id']})
                link = get_internal_link('index', {'type': i['id']})
                xbmcplugin.addDirectoryItem(handle, link, li, True)
    xbmcplugin.endOfDirectory(handle)

def actionGenres(qp):
    response = api('genres', {'type': qp.get('type', '')})
    if response['status'] == 200:
        add_default_headings(qp, "")
        for genre in response['items']:
            li = xbmcgui.ListItem(genre['title'].encode('utf-8'))
            link = get_internal_link('items', {'type': qp.get('type'), 'genre': genre['id']})
            xbmcplugin.addDirectoryItem(handle, link, li, True)
        xbmcplugin.endOfDirectory(handle)
    else:
        notice(response['message'], response['name'])

# List items with pagination
#  qp - dict, query parameters for item filtering
#   title - filter by title
#   type - filter by type
#   category - filter by categroies
#   page - filter by page
def actionItems(qp):
    response = api('items', qp)
    if response['status'] == 200:
        pagination = response['pagination']
        add_default_headings(qp, "s")

        show_items(response['items'])
        show_pagination(pagination, "items", qp)
    else:
        notice(response['message'], response['name'])

# Show items
# If item type is movie with more than 1 episodes - show those episodes
# If item type is serial, docuserial - show seasons
#  if parameter season is set - show episodes
# Otherwise play content
def actionView(qp):
    response = api('items/%s' % qp['id'])
    if response['status'] == 200:
        item = response['item']
        # If serial instance or multiseries film show navigation, else start play
        if item['type'] in ['serial', 'docuserial']:
            if 'season' in qp:
                for season in item['seasons']:
                    if int(season['number']) == int(qp['season']):
                        for episode_number, episode in enumerate(season['episodes']):
                            episode_number += 1
                            episode_title = "s%02de%02d" % (season['number'], episode_number)
                            episode_title = episode_title + " | " + episode['title'] if episode['title'] else episode_title
                            li = xbmcgui.ListItem(episode_title, iconImage=episode['thumbnail'], thumbnailImage=episode['thumbnail'])
                            li.setInfo('Video', addonutils.video_info(item, {
                                'season': int(season['number']),
                                'episode': episode_number
                            }))
                            li.setInfo('Video', {'playcount': int(episode['watched'])})
                            li.setProperty('IsPlayable', 'true')
                            link = get_internal_link('play', {'id': item['id'], 'season': int(season['number']), 'episode': episode_number})
                            xbmcplugin.addDirectoryItem(handle, link, li, False)
                        break
                xbmcplugin.endOfDirectory(handle)
            else:
                for season in item['seasons']:
                    season_title = "Сезон %s" % int(season['number'])
                    li = xbmcgui.ListItem(season_title, iconImage=item['posters']['big'], thumbnailImage=item['posters']['big'])
                    li.setInfo('Video', addonutils.video_info(item, {
                        'season': int(season['number']),
                    }))
                    link = get_internal_link('view', {'id': qp['id'], 'season': season['number']})
                    xbmcplugin.addDirectoryItem(handle, link, li, True)
                xbmcplugin.endOfDirectory(handle)
        elif 'videos' in item and len(item['videos']) > 1:
            for video_number, video in enumerate(item['videos']):
                video_number += 1
                episode_title = "e%02d" % video_number
                episode_title = "%s | %s" % (episode_title, video['title']) if video['title'] else episode_title
                li = xbmcgui.ListItem(episode_title, iconImage=video['thumbnail'], thumbnailImage=video['thumbnail'])
                li.setInfo('Video', addonutils.video_info(item, {
                    'season' : 1,
                    'episode': video_number
                }))
                li.setInfo('Video', {'playcount': int(video['watched'])})
                li.setProperty('IsPlayable', 'true')
                link = get_internal_link('play', {'id': item['id'], 'video': video_number})
                xbmcplugin.addDirectoryItem(handle, link, li, False)
            xbmcplugin.endOfDirectory(handle)
        else:
            return

def actionPlay(qp):
    response = api('items/%s' % qp['id'])
    if response['status'] == 200:
        item = response['item']
        videoObject = None
        liObject = None
        if 'season' in qp:
            # process episode
            for season in item['seasons']:
                if int(qp['season']) != int(season['number']):
                    continue
                for episode_number, episode in enumerate(season['episodes']):
                    episode_number+=1
                    if episode_number == int(qp['episode']):
                        videoObject = episode
                        episode_title = "s%02de%02d" % (season['number'], episode_number)
                        episode_title = "%s | %s" % (episode_title, episode['title']) if episode['title'] else episode_title
                        liObject = xbmcgui.ListItem(episode_title)
                        liObject.setInfo("video", {
                            'season': season['number'],
                            'episode': episode_number
                        })
        elif 'video' in qp:
            # process video
            for video_number, video in enumerate(item['videos']):
                video_number+=1
                if video_number == int(qp['video']):
                    videoObject = video
                    if len(item['videos']) > 1:
                        episode_title = "e%02d" % (video_number)
                        episode_title = "%s | %s" % (episode_title, video['title']) if video['title'] else episode_title
                        liObject = xbmcgui.ListItem(episode_title)
                        liObject.setInfo("video", {
                            'season': 1,
                            'episode': video_number
                        })
                    else:
                        liObject = xbmcgui.ListItem(item['title'])
        else:
            pass

        if 'files' not in videoObject:
            notice("Видео обновляется и временно не доступно!", "Видео в обработке", time=8000)
            return
        url = addonutils.get_mlink(videoObject, quality=DEFAULT_QUALITY, streamType=DEFAULT_STREAM_TYPE)
        liObject.setPath(url)
        xbmcplugin.setResolvedUrl(handle, True, liObject)

def actionSearch(qp):
    kbd = xbmc.Keyboard()
    kbd.setDefault('')
    kbd.setHeading('Поиск')
    kbd.doModal()
    out=''
    if kbd.isConfirmed():
        out = kbd.getText()
    if len(out.decode('utf-8')) >= 3:
        if 'page' in qp:
            qp['page'] = 1
        qp['title'] = out
        nav_internal_link('items', qp)
    else:
        notice("Введите больше символов для поиска", "Поиск")
        nav_internal_link('index')


def actionBookmarks(qp):
    xbmc.log("%s : actionBookmarks. %s" % (__plugin__, str(qp)))
    if 'folder-id' not in qp:
        response = api('bookmarks')
        if response['status'] == 200:
            for folder in response['items']:
                li = xbmcgui.ListItem(folder['title'].encode('utf-8'))
                li.setProperty('folder-id', str(folder['id']).encode('utf-8'))
                li.setProperty('views', str(folder['views']).encode('utf-8'))
                link = get_internal_link('bookmarks', {'folder-id': folder['id']})
                xbmcplugin.addDirectoryItem(handle, link, li, True)
            xbmcplugin.endOfDirectory(handle)
    else:
        # Show content of the folder
        response = api('bookmarks/%s' % qp['folder-id'], qp)
        if response['status'] == 200:
            show_items(response['items'])
            show_pagination(response['pagination'], 'bookmarks', qp)
            xbmcplugin.endOfDirectory(handle)

def actionAlphabet(qp):
    alpha = [
        "А,Б,В,Г,Д,Е,Ё,Ж,З,И,Й,К,Л,М,Н,О,П,Р,С,Т,У,Ф,Х,Ц,Ч,Ш,Щ,Ы,Э,Ю,Я",
        "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z"
    ]
    for al in alpha:
        letters = al.split(",")
        for letter in letters:
            li = xbmcgui.ListItem(letter)
            link = get_internal_link('items', addonutils.dict_merge(qp, {'letter': letter}))
            xbmcplugin.addDirectoryItem(handle, link, li, True)
    xbmcplugin.endOfDirectory(handle)

