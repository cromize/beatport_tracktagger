#!/usr/bin/env python3
import argparse
import urllib3
import core
import sys

from os.path import isfile
from track import Track
from lxml import html

# TODO: make single exit function with pretty info print

# TODO: make musical key retrieval work

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def argsParserInit():
  parser = argparse.ArgumentParser(description="tag audio files with Beatport ID easily.")
  parser.add_argument('-s', '--sync', action='store_true', help='get info from Beatport')
  parser.add_argument('-t', '--tag-files', action='store_true', help='update tags in audio files')
  parser.add_argument('-c', '--clean-tags', action='store_true', help='clean tags in audio files')
  parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
  parser.add_argument('-a', '--artwork', action='store_true', help='update track artwork')
  parser.add_argument('-r', '--recursive', action='store_true', help='run recursive')
  parser.add_argument('-z', '--fuzzy', action='store_true', help='try to fuzzy match')
  parser.add_argument('-i', '--input', help='specify input', default='')
  parser.add_argument('-f', '--force', action='store_true', help='force tag overwrite')
  parser.add_argument('--save-db', help='save tags to database', default='local.db')
  parser.add_argument('--load-db', help='load tags from database', default='local.db')
  return parser

if __name__ == "__main__": 
  print('*** welcome beatport_tagger ***')

  # main db
  db = core.Database()

  # input parser
  input_parser = argsParserInit()
  args = input_parser.parse_args()

  # args check
  if (len(sys.argv) <= 1):
    input_parser.print_help()  
    sys.exit(0)

  # load existing db
  if isfile(args.load_db):
    print('\n** database found! loading data')
    db.loadJSON(args.load_db)
    print(f'** number of tracks in db: {len(db.db)}' )

  # scan for flac and mp3 files
  work_files = core.scanFiletype(args.input, args.recursive)

  # clean file tags
  if args.clean_tags:
    print("\n** cleaning tags")
    for idx, f in enumerate(work_files):
      print(f'{idx+1}/{len(work_files)} - {f}')
      Track.cleanTags(f)
    sys.exit(1)

  # query beatport id using fuzzy name matching
  if args.fuzzy:
    print("\n** getting tags using fuzzy matching")
    db.track_count = len(work_files)
    core.spawnWorkers(core.doFuzzyMatch, work_files, db)
  else:
    work_files = db.scanBeatportID(work_files)

  # get tags from beatport
  if args.sync:
    print('\n** getting tags from beatport')
    core.spawnWorkers(core.addTrackToDB, work_files, db)
    db.saveJSON(args.save_db)

  # tag audio files
  if args.tag_files: 
    print('\n** updating audio tags')
    i = 0
    for k, v in db.db.items():
      # for scanned files only
      if "file_path" in v.__dict__:
        print(f'{i+1}/{db.track_count} - {v.file_name}')
        v.fileTagsUpdate(args.force)
        i += 1

  # save artwork
  if args.artwork:
    print("\n** saving artwork")
    i = 0
    for k, v in db.db.items():
      if "file_path" in v.__dict__:
        print(f'{i+1}/{db.track_count} - {v.file_name}')
        v.saveArtwork()
        i += 1

  print('\n** all done')

