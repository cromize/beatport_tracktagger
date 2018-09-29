#!/bin/bash

shopt -s globstar
die() {
  printf '%s\n' "$1" >&2
  exit 1
}

# input args
input_folder=
output_folder=
while :; do
  case $1 in
    # --input
    -i|--input)
      if [ "$2" ]; then
        input_folder=("$(readlink -nf $2)")
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

files="$input_folder"/**/*.{wav,aiff}
audio_files_count="${#files[@]}"

export audio_files_count
export input_folder
export output_folder

echo "files: $audio_files_count"

# input arg
if [ ! "$input_folder" ]; then
  command='sox {}' 
else
  command='sox "'"$input_folder"/{/}'"'
fi

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

echo $command

# TODO: make skip system
# TODO: BUG: it fails, when input_folder array is empty
# run in parallel
parallel -k -j30 --env audio_files_count,output_folder,input_folder $command ::: "${input_folder[@]}"/**/*.{wav,aiff}

