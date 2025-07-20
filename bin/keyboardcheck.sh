#!/bin/bash

# List of relevant keyboard config files
files=(
    "$HOME/.xprofile"                # sets LANG, XMODIFIERS, fcitx env vars
    "$HOME/.profile"                 # sets LANG, XMODIFIERS, fcitx env vars
    "$HOME/.XCompose"                # optional, custom compose definitions
    "$HOME/.Xprofile"                # optional, custom compose definitions
    "$HOME/.xinit"                # optional, custom compose definitions
    "$HOME/.xinitrc"                # optional, custom compose definitions
    "$HOME/.bashrc"                # optional, custom compose definitions
    "$HOME/.bash_aliases"                # optional, custom compose definitions
    "/etc/default/keyboard"          # persists keyboard layout/options across sessions
    # "/usr/share/X11/locale/en_US.UTF-8/Compose"   # system Compose table
)

# this function prints the file list and copies them to clipboard
myfuncoriginal() {
# Print grepped lines and their file
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        # grep --with-filename "win_space_toggle" "$file"
        echo -e "\n====================  $file  file below: ========================================\n"
        cat "$file"
    else
        echo "The $file  file does not exist"
    fi
done
    echo -e "\n====================  running: setxkbmap -print -verbose 10 ========================================\n"
    setxkbmap -print -verbose 10

}
# this function checks which files have "caps" keyword in them
myfunc() {
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        # grep --with-filename "win_space_toggle" "$file"
        echo -e "\n====================  $file  file below: ========================================\n"
        cat "$file" | grep ".*caps*"
    else
        echo "The $file  file does not exist"
    fi
done
    echo -e "\n====================  running: setxkbmap -print -verbose 10 ========================================\n"
    setxkbmap -print -verbose 10 | grep "*caps*"

}
myfunc | tee >(xclip -selection clipboard)