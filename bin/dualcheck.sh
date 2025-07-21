list=("/home/petteri/repos/github/dual-function-keys/my-mappings.yaml" "/etc/interception/udevmon.d/my-udevmon.yaml")
commandlist=(
    "sudo systemctl status udevmon" 
    "ls -l $HOME/repos/github/dual-function-keys/" 
    "ls -l /etc/interception" 
    "xinput list"
)

# the function reads the file list, cats them, then copies to the clipboard
myfunc() {
for file in "${list[@]}"; do
    echo -e "\nReading $file ===================\n"
    cat "$file"

done
echo -e "\n"
for cmd in "${commandlist[@]}"; do
    echo "$cmd"
    # prefixing the command with a space to make sure that the command doesnt mix '-' characters
    eval " $cmd"
done
}


myfunc | tee >(xclip -selection clipboard)