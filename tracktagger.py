#!/usr/bin/env python3
import threading
import argparse
import requests
import mutagen
import queue
import json
import glob
import sys
import re
import os

from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture, FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from os.path import isfile
from pathlib import Path
from lxml import html

num_worker_threads=20

# TODO: add option for recursive

class Track:
  json_database = []
  database = dict()
  
  processing_iterator = 0

  # from file scan
  track_count = 0

  def __init__(self, beatport_id = 0):
    self.beatport_id = beatport_id
    self.artists = []
    self.title = ''
    self.album = ''
    self.remixer = ''
    self.length = ''
    self.released = ''
    self.bpm = ''
    self.key = ''
    self.genre = ''
    self.label = ''
    self.file_name = ''

  def queryPage(self):
    try:
      page = requests.get('https://www.beatport.com/track/aa/' + self.beatport_id)
    except Exception as e:
      print(e)
      print(f"** error cannot get track info!")
      sys.exit(1)
    return html.fromstring(page.content)

  # get tags using beatport id
  def getTags(self):
    tree = self.queryPage()
    artistCount = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/div[1]/span[2]/a')
    artistCount = len(artistCount)

    for artist in range(1, artistCount + 1):
      path = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/div[1]/span[2]/a[' + str(artist) + ']/text()')
      self.artists.append(path.pop())

    # Get info from beatport
    self.title = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[1]/div[1]/h1[1]/text()').pop()
    self.remixer = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[1]/div[1]/h1[2]/text()').pop()
    self.length = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[1]/span[2]/text()').pop()
    self.released = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[2]/span[2]/text()').pop()
    self.bpm = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[3]/span[2]/text()').pop()
    self.key = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[4]/span[2]/text()').pop()
    self.genre = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[5]/span[2]/a/text()').pop()
    self.label = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[6]/span[2]/a/text()').pop()
    self.album = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[1]/li/@data-ec-name').pop()
    self.artwork_url = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[1]/li/a/img').pop().attrib['src']

  def printTrackInfo(self):
    print ('track: ', end='')
    x = 1
    for artist in self.artists:   # for multiple artist pretty print
      print(artist, end='')
      if len(self.artists) > 1 and x < len(self.artists):
        print (', ', end='')
      x += 1

    print (f' - {self.title} ({self.remixer})')
    print (f'Album: {self.album}\n'
           f'Length: {self.length}\n'
           f'Released: {self.released}\n'
           f'BPM: {self.bpm}\n'
           f'Key: {self.key}\n'
           f'Genre: {self.genre}\n'
           f'Label: {self.label}\n'
           f'Beatport ID: {self.beatport_id}\n')
    print ('')
    
  def openDatabaseJSON(src):
    with open(src, 'r') as f:
      Track.json_database = f.readlines()

  def saveDatabaseJSON(src):
    with open(src, 'w') as f:
      for k, v in Track.database.items():
        import copy       # raw object copy, to make true duplicate
        vv = copy.copy(v) 
        if "file_path" in vv.__dict__:
          del vv.__dict__["file_path"]
        track_json = json.dumps(vv.__dict__)
        f.write(track_json + '\n')

  def loadTracks():
    for track in Track.json_database:
      track_object = Track()
      track_object.__dict__ = json.loads(track)
      Track.database[track_object.beatport_id] = track_object

  def scanFiles(src):
    filetypes = '.flac', '.mp3'
    outputFiles = []
    if Path(src).is_file():           # single file
      files = [Path(src)]
    elif args.recursive:              # recursive 
      files = Path(src).glob('**/*')
    else:
      files = Path(src).glob('*')     # input folder

    # for every file that matches filetype and beatport id in db:
    #   assing scanned path to db
    for f in files:
      if Path(f).suffix in filetypes: 
        if beatport_id_pattern.match(Path(f).name):
          beatport_id = beatport_id_pattern.match(Path(f).name).group()[:-1]
          if beatport_id in Track.database.keys():
            Track.database[beatport_id].file_path = Path(f)
          outputFiles.append(Path(f))
          Track.track_count += 1
    return outputFiles

  def trackInDB(beatport_id):
    if beatport_id in Track.database:
      return True
    return False

  # update tags in valid scanned files
  def fileTagsUpdate(self):
    path = self.file_path
    if Path(self.file_name).suffix == ".flac":
      audiof = FLAC(path)  
    elif Path(self.file_name).suffix == ".mp3":
      audiof = EasyID3(path)  

    # single artist
    if len(self.artists) == 1: audiof['ARTIST'] = self.artists
    # multiple artists
    else:
      temp = ""
      for i, artist in enumerate(self.artists):
        temp += artist
        if i < len(self.artists) - 1:
           temp += ", "
      audiof['ARTIST'] = [temp]

    audiof['DATE'] = self.released[:4]
    audiof['GENRE'] = self.genre
    audiof['ORGANIZATION'] = self.label
    audiof['TITLE'] = self.title + " (" + self.remixer + ")"
    audiof['ALBUM'] = self.album
    audiof.save()

  # query and save artwork
  # artwork(500x500)
  def saveArtwork(self):
    img = requests.get(self.artwork_url).content
    if Path(self.file_name).suffix == ".flac":
      audiof = FLAC(self.file_path)  
      img = Picture()
      img.type = 3
      img.desc = 'artwork'
      img.data = requests.get(self.artwork_url).content
      audiof.add_picture(img)
    elif Path(self.file_name).suffix == ".mp3":
      audiof = ID3(self.file_path)  
      audiof.add(mutagen.id3.APIC(3, 'image/jpeg', 3, 'Front cover', img))
    audiof.save()

  def cleanTags(filepath):
    if Path(filepath).suffix == ".flac":
      audiof = FLAC(filepath)  
      audiof.clear_pictures()
    elif Path(filepath).suffix == ".mp3":
      audiof = EasyID3(filepath)  
      audiof.delete()
    audiof.save()

  def addTrackToDatabase(filepath):
    filename = Path(filepath).name

    # if is valid beatport file
    if beatport_id_pattern.match(filename):
      beatport_id = beatport_id_pattern.match(filename).group()[:-1]

      if Track.trackInDB(beatport_id):
        Track.processing_iterator += 1
        print(f'{Track.processing_iterator}/{Track.track_count} - (Already in DB) {filename}')
        return Track.processing_iterator

      # create and get tags
      track = Track(beatport_id)
      track.file_path = str(Path(filepath))
      track.file_name = filename

      # try 10 times
      for tries in range(10):
        try:
          track.getTags()
          break
        except:
          pass

      Track.processing_iterator += 1
      Track.database[track.beatport_id] = track
      print(f"{Track.processing_iterator}/{Track.track_count} - {track.file_name}") 

      if args.verbose:
        track.printTrackInfo()

    return Track.processing_iterator

  # add all valid files to database
  def processFiles(files):
    q = queue.Queue()
    threads = []
    for i in range(num_worker_threads):
      t = threading.Thread(target=Track.worker, args=(Track.addTrackToDatabase,q))
      t.start()
      threads.append(t)

    for f in files:
      q.put(f) 

    # wait for workers
    q.join()
    
    # kill workers
    for i in range(num_worker_threads):
      q.put(None)
    for t in threads:
      t.join() 

  def worker(work, queue):
    while True:
      item = queue.get()
      if item is None:
        break
      work(item)
      queue.task_done()
    
def argsParserInit():
  parser = argparse.ArgumentParser(description="tag audio files with Beatport ID easily.")
  parser.add_argument('-s', '--sync', action='store_true', help='get info from Beatport')
  parser.add_argument('-t', '--tag-files', action='store_true', help='update tags in audio files')
  parser.add_argument('-c', '--clean-tags', action='store_true', help='clean tags in audio files')
  parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
  parser.add_argument('-a', '--artwork', action='store_true', help='update track artwork')
  parser.add_argument('-r', '--recursive', action='store_true', help='run recursive')
  parser.add_argument('-i', '--input', help='specify input', default='')
  parser.add_argument('--save-db', help='save tags to database', default='tracks.db')
  parser.add_argument('--load-db', help='load tags from database', default='tracks.db')
  return parser

if __name__ == "__main__": 
  print('*** welcome beatport_tagger ***')

  # input parser
  input_parser = argsParserInit()
  args = input_parser.parse_args()

  # args check
  if (len(sys.argv) <= 1):
    input_parser.print_help()  
    sys.exit(0)

  # load existing db
  if isfile(args.load_db):
    print('\n** database found! loading data...')
    Track.openDatabaseJSON(args.load_db)
    Track.loadTracks()
    print(f'** number of tracks in db: {len(Track.database)}' )

  # scan for flac files
  beatport_id_pattern = re.compile('^[0-9]+[_]')
  work_files = Track.scanFiles(args.input)

  # get tags from beatport
  if args.sync:
    print('\n** getting tags from beatport')
    Track.processFiles(work_files)
    Track.saveDatabaseJSON('tracks.db')

  # tag audio files
  if args.tag_files: 
    print('\n** updating audio tags...')
    i = 1
    for k, v in Track.database.items():
      # for scanned files only
      if "file_path" in v.__dict__:
        print(f'{i}/{Track.track_count} - {v.file_name}')
        v.fileTagsUpdate()
        i += 1

  # clean file tags
  if args.clean_tags:
    print("\n** clearing tags")
    for idx, f in enumerate(work_files):
      print(f'{idx+1}/{len(work_files)} - {f}')
      Track.cleanTags(f)

  # save artwork
  if args.artwork:
    print("\n** saving artwork")
    for idx, (k, v) in enumerate(Track.database.items()):
      if "file_path" in v.__dict__:
        print(f'{idx+1}/{Track.track_count} - {v.file_name}')
        v.saveArtwork()

  print('\n** all done')
