list=("/home/petteri/repos/github/dual-function-keys/mappings.yaml" "/etc/interception/udevmon.d/my-udevmon.yaml")


# the function reads the file list, cats them, then copies to the clipboard
myfunc() {
for file in "${list[@]}"; do
    echo -e "\nReading "$file" ===================\n"
    echo -e "\nReading $file ===================\n"
    cat "$file"

done
}

myfunc | tee >(xclip -selection clipboard)