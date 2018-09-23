#!/bin/bash

# TODO: add output folder arg
shopt -s globstar

echo "Tool for converting wav, aiff files to flac (using sox)"
echo

audio_files=(**/*.{wav,aiff})
audio_files_count="${#audio_files[@]}"
export audio_files_count

parallel -k --env audio_files_count 'sox {} {.}.flac | echo "{#}/$audio_files_count) {}"' ::: **/*.{wav,aiff}

