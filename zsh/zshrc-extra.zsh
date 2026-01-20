# this function below is potentially dangerous and shouldnt be used with rm commands
xc() {
  local cmd
  printf -v cmd '%q ' "$@"   # build a shell-replayable command line

  {
    printf 'PWD: %s\n' "$PWD"
    printf 'COMMAND: $ %s\n' "$cmd"
    echo
    eval "$cmd"              # re-parse → aliases expand
  } | xclip -selection clipboard
}
# activate the py310 conda environment (c a p  )
cap() {
	conda activate py310
}




