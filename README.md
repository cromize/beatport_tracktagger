Beatport Tracktagger
======

This project is a rework of an old beatport ID tagging tool. It's capable of getting useful tags from beatport and assigning them into audio file.

Installation
-----
```
pip3 install lxml requests mutagen
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

# get tags and artwork from beatport and update local files
./tracktagger.py -t -s -a

# run from supplied path (including sub-folders)
./tracktagger.py -t -s -a -i some/path

```

Supported formats
------

* FLAC

Libraries Used
-----
* requests for pulling webpage
* lxml for parsing info
* mutagen for assigning tags to files

TODO
-----
* more audio formats
* website UI

