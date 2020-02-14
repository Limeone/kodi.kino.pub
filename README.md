[![Build Status](https://travis-ci.org/quarckster/kodi.kino.pub.svg?branch=master)](https://travis-ci.org/quarckster/kodi.kino.pub)

Kodi addon for kino.pub
=======================================

Kodi 17 is a minimal supported version.

The most notable features:

* feature to choose video quality before playing
* configurable start screen items
* added custom context menu items: "Буду смотреть", "Отметить как просмотренное", "Изменить закладки", "Комментарии kino.pub"
* watch and resume points are synced across multiple devices
* new folders "Горячее" and "Недосмотренные"
* support of Trakt.tv
* support of 4k
* support of [inputstream.adaptive](https://github.com/peak3d/inputstream.adaptive) addon



Manual installation
===================

* download the latest version here https://github.com/quarckster/kodi.kino.pub/releases/latest
* go to Add-on manager https://kodi.wiki/view/Add-on_manager
* choose "Install from ZIP file"

Sync media to local Library
===========================

* support saving movies and tvhows from "Горячие" and "Популярные" categories to local library
* support saving subscribed tvhows to local library
* support skip Anime on saving "Горячие" and "Популярные" media
* support manual adding of single movies and tvhows to local library
* support removing movies and tvhows from local library and blocking for future saving
* support updating saved to local library items that are not in "Горячие" and "Популярные" anymore
* support rescanning saved movies with translations in separate files after merging to one media
* support removing all saved media and disabling saving to local library


#### All saved media is stored in next directories:
* Tvshows: <DIRECTORY_FROM_SETTINGS>/KinoPub/Сериалы
* Movies: <DIRECTORY_FROM_SETTINGS>/KinoPub/Фильмы

Movies are saved in separate folder for each movie

Descriptions, media info, arts, etc are fetched from kodi skrappers

[Adding video sources to Kodi](https://kodi.wiki/view/Adding_video_sources)

#### Saving media with whatching status:

Add next info to [advancedsettings.xml](https://kodi.wiki/view/Advancedsettings.xml)

```xml
<advancedsettings>
  <videolibrary>
    <importwatchedstate>true</importwatchedstate>
    <importresumepoint>true</importresumepoint>
  </videolibrary>
</advancedsettings>
```

#### Setting up plugin for using Local Library

* Go to plugin settings
* Локальная Библиотека > Включить синхронизацию библиотеки
* Choose root directory for storing synced media
* Select sections that should be synced to local library
* Save settings
* Go to plugin settings
* Локальная Библиотека > Запустить синхронизацию
* Close settings

Local library sync proceed right after Kodi instance started and repeat each hour while Kodi instance is running


Legacy plugin
=============

If you need the latest version of the original plugin you can download it here https://plugins.service-kp.com/kodi/video.kino.pub/video.kino.pub-1.2.1.zip
