#!/bin/bash

MAX_PARALLEL=20

IFS=$'\n'
shopt -s globstar

die() {
  printf '%s\n' "$1" >&2
  exit 1
}

# extract input args
input_folder="$PWD"
output_folder=
while :; do
  case $1 in
    # --input
    -i|--input)
      if [ "$2" ]; then
        unset input_folder
        input_folder="$(readlink -nf $2)"
        shift
      fi
      ;;

    # --output
    -o|--output)
      if [ "$2" ]; then
        output_folder="$(readlink -nf $2)"
        if [ ! -d "$output_folder" ]; then
          # folder doesn't exist
          mkdir "$output_folder"
        fi
        shift
      else
        output_folder={.}.flac
      fi
      ;;
    *)
      break
  esac
  shift
done

echo "tool for converting wav, aiff files to flac (using sox)"
echo "by cromize"
echo

# all work files
files=("$input_folder"/**/*.{wav,aiff})
audio_files_count="${#files[@]}"

export audio_files_count
export input_folder
export output_folder

echo "files: $audio_files_count"

# input arg
command='sox {}'

# output arg
if [ ! "$output_folder" ]; then
  command+=' {.}.flac'
else
  command+=' "'"$output_folder"/{/.}.flac'"'
fi

# print iteration info
# ********
command+=' | echo "{#}/$audio_files_count)" '

if [ ! "$output_folder" ]; then
  command+='{}'
else
  command+="$output_folder"/{/.}.flac
fi
# ********

# TODO: make skip system

# run in parallel
parallel -k -j$MAX_PARALLEL --env audio_files_count,output_folder,input_folder $command ::: "${input_folder[@]}"/**/*.aiff "${input_folder[@]}"/**/*.wav

