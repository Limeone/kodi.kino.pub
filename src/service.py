#!/usr/bin/python
import xbmc

from resources.lib.addon_library import AddonLibrary

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if AddonLibrary.ENABLED:
            AddonLibrary.sync_sections()
        if monitor.waitForAbort(60 * 30):
            break  # wait 30 minutes
