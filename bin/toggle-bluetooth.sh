#!/bin/bash



# check if the blueman-manager is open and if not, turn it on
# the if condition is true if the blueman was found
if /usr/bin/pgrep blueman-manager >> /dev/null ; then
    /usr/bin/wmctrl -c blueman-manager
else
    # case where blueman was not on so lets start it
    /usr/bin/blueman-manager &
fi