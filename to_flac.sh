#!/bin/bash

# TODO: add output folder arg
shopt -s globstar

echo "Tool for converting wav, aiff files to flac (using sox)"
echo

wav_files=(**/*.wav)
wav_files_count="${#wav_files[@]}"
export wav_files_count

parallel -k --env wav_files_count 'sox {} {.}.flac | echo "{#}/$wav_files_count) {}"' ::: **/*.wav

