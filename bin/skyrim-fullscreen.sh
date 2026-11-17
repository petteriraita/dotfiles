#!/bin/sh
# Skyrim can clear i3's initial fullscreen state while creating its window.
sleep 3
i3-msg '[class="^steam_proton$" title="^Skyrim Special Edition$"] fullscreen enable' >/dev/null
