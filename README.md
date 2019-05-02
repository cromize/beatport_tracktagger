Beatport Tracktagger
======

[![Build Status](https://travis-ci.org/cromize/beatport_tracktagger.svg?branch=master)](https://travis-ci.org/cromize/beatport_tracktagger)

Ever bought tracks from beatport that didn't have tags in it? Or you simply wanted to tag files automatically, by scraping?

This multithread tagging tool uses fuzzy string matching to do the work. It's capable of getting useful tags from beatport  (`-s`) and assigning them into audio file (`-t`).

Even though it's able to tag files only using title and artist in attributes (`-z`), tagger works best with beatport id in front of the filename e.g. 5024319_track.mp3 (that's format from bought beatport tracks).

Fuzzy matching uses probabilities, instead of exact 'yes' or 'no' matching. It can return false match, when info is not accurate enough or when beatport doesn't know about the release yet.

Dependency: newest Python 3

Installation
-----
```
# install dependencies
pip3 install lxml urllib3 mutagen fuzzywuzzy

# clone this project
git clone https://github.com/cromize/beatport_tracktagger.git

# run
./tracktagger.py -t -s -a -i some/path
```

Usage
-----
```
# get tags from beatport into local db, doesn't update actual files
./tracktagger.py -s

# tag files with tags from local db
./tracktagger.py -t

# save artwork from beatport (500x500)
./tracktagger.py -a

# clean all tags with artwork
./tracktagger.py -c

# run recursively
./tracktagger.py -r

# scrape info from file and match using fuzzy matching
./tracktagger.py -z

# get tags and artwork from beatport and update local files
./tracktagger.py -t -s -a

# run from supplied path with all possible options (including sub-folders)
./tracktagger.py -tsari some/path

```

Supported formats
------

* FLAC
* MP3

Libraries Used
-----
* urllib3 for pulling webpage
* lxml for parsing info
* mutagen for assigning tags to files
* fuzzywuzzy for fuzzy string matching

TODO
-----
* tests
* website UI

