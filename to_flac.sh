#!/bin/bash

# TODO: add output folder arg
# TODO: better printout
shopt -s globstar

#LIST=$(find $1 -name "*.wav" -o -name "*.aiff" -exec {} \;)
#file_count=$(find $1 -name "*.wav" -o -name "*.aiff" -exec {} \; | wc -c)

echo "Tool for converting wav, aiff files to flac (using sox)"
echo

i=1
for file in **/*.wav; do
  sox "$file" "${file%.*}.flac"
  echo "$i) $file"
  ((i++))
done
