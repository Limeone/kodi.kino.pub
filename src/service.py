#!/usr/bin/python
import xbmc

from resources.lib.addon_library import AddonLibrary

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if AddonLibrary.ENABLED:
            synced_ids = AddonLibrary.SyncSectionsToVideoLibray()
            # Do not update just proceeded items
            AddonLibrary.UpdateSavedMedia(exclude=synced_ids)
            # Force kodi to update Video Library
            AddonLibrary.ScanVideoLibrary()
        if monitor.waitForAbort(60 * 60):
            break  # wait 1 hour
