#!/usr/bin/env python3
import argparse
import requests
import json
import mutagen
import glob
import re
import sys
import os
import threading
import queue

from lxml import html
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture, FLAC
from os.path import isfile

num_worker_threads=20

# TODO: wont run for single file

# TODO: get working directory from program location or input source folder, instead of current working dir

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
    self.file_type = ''

  def queryPage(self):
    try:
      page = requests.get('https://www.beatport.com/track/aa/' + self.beatport_id)
    except requests.exceptions.RequestException as e:
      print(f"Error cannot get track info!")
      sys.exit(1)
    return html.fromstring(page.content)

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
    print ('Track: ', end='')

    x = 1
    for artist in self.artists:
      print (artist, end='')
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
    
  def openDatabaseJSON(file):
    with open(file, 'r') as file:
      Track.json_database = file.readlines()

  def saveDatabaseJSON(file):
    with open(file, 'w') as file:
      for k, v in Track.database.items():
        track_json = json.dumps(v.__dict__)
        file.write(track_json + '\n')

  def loadTracks():
    for track in Track.json_database:
      track_object = Track()
      track_object.__dict__ = json.loads(track)
      Track.database[track_object.beatport_id] = track_object

  def scanFiles(input):
    filetypes = '.flac', '.mp3'
    files = glob.glob(os.path.join(input, '**'), recursive=True)
    outputFiles = []

    # For flacs, mp3s 
    for f in files:
      # win
      if os.name == 'nt':
        filename = f.split('\\')[-1]
      # linux 
      else:
        filename = f.split('/')[-1]

      # if ends with correct filetype
      for filetype in filetypes:
        if filename.lower().endswith(filetype):
          if beatport_id_pattern.match(filename):
            outputFiles.append(f)
            Track.track_count += 1
            break
    return outputFiles

  def trackInDB(beatport_id):
    if beatport_id in Track.database:
      return True
    return False

  def fileTagsUpdate(self):
    path = self.file_path
    if self.file_type == ".flac":
      audiof = FLAC(path)  
    elif self.file_type == ".mp3":
      audiof = EasyID3(path)  

    # single artist
    if len(self.artists) == 1: audiof['ARTIST'] = self.artists
    else:
      temp = ""
      count = 0

      # multiple artists
      for artist in self.artists:
        temp += artist
        if count < len(self.artists) - 1:
           temp += ", "
        count += 1
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
    if self.file_type == ".flac":
      audiof = FLAC(self.file_path)  
    elif self.file_type == ".mp3":
      audiof = ID3(self.file_path)  
    img = requests.get(self.artwork_url).content
    audiof.add(mutagen.id3.APIC(3, 'image/jpeg', 3, 'Front cover', img))
    audiof.save()

  def cleanTags(filepath):
    if filepath.endswith(".flac"):
      audiof = FLAC(filepath)  
    elif filepath.endswith(".mp3"):
      audiof = ID3(filepath)  
    audiof.delete()
    audiof.save()

  def addTrackToDatabase(filepath):
    # win
    if os.name == 'nt':
      filename = filepath.split('\\')[-1]
    # linux 
    else:
      filename = filepath.split('/')[-1]

    print("omg:", filepath)

    # if is valid beatport file
    if beatport_id_pattern.match(filename):
      beatport_id = beatport_id_pattern.match(filename).group()[:-1]

      if Track.trackInDB(beatport_id):
        Track.processing_iterator += 1
        print(f'{Track.processing_iterator}/{Track.track_count} - (Already in DB) {filename}')
        return Track.processing_iterator

      # create and get tags
      track = Track(beatport_id)
      track.file_path = os.path.abspath(filepath)
      track.file_name = filename

      # fill filetype
      if track.file_name.lower().endswith(".flac"):
        track.file_type = ".flac"
      elif track.file_name.lower().endswith(".mp3"):
        track.file_type = ".mp3"

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
  parser.add_argument('-i', '--input', help='specify input', default='')
  parser.add_argument('--save-db', help='save tags to database', default='tracks.db')
  parser.add_argument('--load-db', help='load tags from database', default='tracks.db')
  return parser

if __name__ == "__main__": 
  print('welcome beatport_tagger\n')

  # input parser
  input_parser = argsParserInit()
  args = input_parser.parse_args()

  # args check
  if (len(sys.argv) <= 1):
    input_parser.print_help()  
    sys.exit(0)

  # scan for flac files
  beatport_id_pattern = re.compile('^[0-9]+[_]')
  flac_files = Track.scanFiles(args.input)

  # load existing db
  if isfile(args.load_db):
    print('Database found! Loading data...')
    Track.openDatabaseJSON(args.load_db)
    Track.loadTracks()
    print(f'Number of tracks in db: {len(Track.database)}' )

  # get tags from beatport
  if args.sync:
    Track.processFiles(flac_files)
    Track.saveDatabaseJSON('tracks.db')

  # tag audio files
  if args.tag_files: 
    print('Updating audio tags...')
    i = 1
    for k, v in Track.database.items():
      print(f'{i}/{Track.track_count} - {v.file_name}')
      v.fileTagsUpdate()
      i += 1

  # clean file tags
  if args.clean_tags:
    print("Clearing tags")
    for idx, file in enumerate(flac_files):
      print(f'{idx+1}/{len(flac_files)} - {file}')
      Track.cleanTags(file)

  # save artwork
  if args.artwork:
    print("Saving artwork")
    for idx, (k, v) in enumerate(Track.database.items()):
      print(f'{idx+1}/{Track.track_count} - {v.file_name}')
      v.saveArtwork()

  print('Done')
