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
from mutagen.flac import FLAC
from os.path import isfile

num_worker_threads=20

# TODO: add artwork query

# TODO: make it scan filepath at start. when we tranfer our db to diff PC, filepath will differ

# TODO: get working directory from program location, instead of current working dir

class Track:
  json_database = []
  database = []
  
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
    self.file_path = ''

  def getTags(self):
    try:
      page = requests.get('https://www.beatport.com/track/aa/' + self.beatport_id)
    except requests.exceptions.RequestException as e:
      print (f"Error cannot get track info!")
      sys.exit(1)

    tree = html.fromstring(page.content)

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

    # query artwork
    # save as file
    artwork = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[1]/li/a/img').pop()
    with open(self.title + '.jpg', 'wb') as f:
      img = requests.get(artwork.attrib['src']).content
      f.write(img)

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
           f'Beatport ID: {self.beatport_id}\n'
           f'Path: {self.file_path}')
    print ('')
    
  def openDatabaseJSON(file):
    with open(file, 'r') as file:
      Track.json_database = file.readlines()

  def saveDatabaseJSON(file):
    with open(file, 'w') as file:
      for track in Track.database:
        track_json = json.dumps(track.__dict__)
        file.write(track_json + '\n')

  def loadTracks():
    for track in Track.json_database:
      track_object = Track()
      track_object.__dict__ = json.loads(track)
      Track.database.append(track_object)

  def scanFiles(input):
    filetypes = '.flac'
    files = glob.glob(os.path.join(input, '**'), recursive=True)
    outputFiles = []

    # For flacs only
    for f in files:
      file_path = f

      # win
      if os.name == 'nt':
        f = f.split('\\')[-1]
      # linux 
      else:
        f = f.split('/')[-1]

      # if match, add to list
      if f.lower().endswith(filetypes):
        if beatport_id_pattern.match(f):
          outputFiles.append(file_path)
          Track.track_count += 1
    return outputFiles

  def trackInDB(beatport_id):
    for track in Track.database:
      if track.beatport_id == beatport_id: return True
    return False

  def fileTagsUpdate(self):
    path = self.file_path
    file = FLAC(path)  

    # single artist
    if len(self.artists) == 1: file['ARTIST'] = self.artists
    else:
      temp = ""
      count = 0

      # multiple artists
      for artist in self.artists:
        temp += artist
        if count < len(self.artists) - 1:
           temp += ", "

        count += 1
      file['ARTIST'] = [temp]

    #file['TBPM'] = self.bpm
    file['DATE'] = self.released[:4]
    file['GENRE'] = self.genre
    file['ORGANIZATION'] = self.label
    file['TITLE'] = self.title + " (" + self.remixer + ")"
    file['ALBUM'] = self.album

    file.save()

  def cleanTags(filepath):
    file = FLAC(filepath)
    file.delete()

  def addTrackToDatabase(filepath):
    # win
    if os.name == 'nt':
      filename = filepath.split('\\')[-1]
    # linux 
    else:
      filename = filepath.split('/')[-1]

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

      # try 10 times
      for tries in range(10):
        try:
          track.getTags()
          break
        except:
          pass

      Track.processing_iterator += 1
      Track.database.append(track)
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
  parser.add_argument('-i', '--input', help='specify input', default='')
  parser.add_argument('--save-db', help='save tags to database', default='tracks.db')
  parser.add_argument('--load-db', help='load tags from database', default='tracks.db')
  return parser

if __name__ == "__main__": 
  print('beatport_tagger v0.5.0\n')

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
    for track in Track.database:
      track.fileTagsUpdate()
      print(f'{i}/{Track.track_count} - {track.file_name}')
      i += 1

  # clean file tags
  if args.clean_tags:
    for file in flac_files:
      Track.cleanTags(file)

  print('Done')
