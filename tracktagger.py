#!/usr/bin/env python3
import argparse
import requests
import json
import mutagen
import glob
import re
import sys
import os

from lxml import html
from mutagen.flac import FLAC
from os.path import isfile

class Track:
  json_database = []
  database = []

  # from file scan
  track_count = 0

  def __init__(self, beatport_id = 0):
    self.beatport_id = beatport_id

    self.artists = []
    self.title = 'N/A'
    self.album = 'N/A'
    self.remixer = 'N/A'
    self.length = 'N/A'
    self.released = 'N/A'
    self.bpm = 'N/A'
    self.key = 'N/A'
    self.genre = 'N/A'
    self.label = 'N/A'
    self.file_name = 'N/A'
    self.file_path = 'N/A'

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
      path = tree.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/div[1]/span[2]/a[' + str(artist) +\
          ']/text()')

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

  def scanFiles():
    filetypes = '.flac'
    files = glob.glob('**', recursive=True)
    outputFiles = []

    # For wavs only
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

    #file['BPM'] = self.bpm
    file['DATE'] = self.released[:4]
    file['GENRE'] = self.genre
    file['ORGANIZATION'] = self.label
    #file['VERSION'] = self.remixer
    #file['RELEASEDATE'] = self.released
    file['TITLE'] = self.title + " (" + self.remixer + ")"
    file['ALBUM'] = self.album

    print(file.pprint())
    file.save()

  def cleanTags(filepath):
    file = FLAC(filepath)
    file.delete()

  def addTrackToDatabase(filepath):
    count_added = 0
    # win
    if os.name == 'nt':
      filename = filepaht.split('\\')[-1]
    # linux 
    else:
      filename = filepath.split('/')[-1]

    # if is valid beatport file
    if beatport_id_pattern.match(filename):
      beatport_id = beatport_id_pattern.match(filename).group()[:-1]

      if Track.trackInDB(beatport_id):
        print('Track is already in DB!')
        return count_added

      # create and get tags
      track = Track(beatport_id)
      track.file_path = filepath
      track.file_name = filename
      track.getTags()

      if args.verbose:
        track.printTrackInfo()

      if args.ask:
        if askUser('Found a track, is this correct? (Y/N/Enter): ', enter=True):
          count += 1
          Track.database.append(track)
          print('Track added to database.\n')
        else:
          print('\nIgnoring...\n')
      else:
        Track.database.append(track)
        print('Track added to database.\n') 
    return count_added

  # add track to db
  def processFiles(files):
    count = 1
    for f in files:
      print(f"{count}/{Track.track_count} - {f}") 
      Track.addTrackToDatabase(f)
      count += 1
    
def argsParserInit():
  parser = argparse.ArgumentParser(description="tag audio files with Beatport ID easily.")
  parser.add_argument('-s', '--sync', action='store_true', help='get info from Beatport')
  parser.add_argument('-t', '--tag-files', action='store_true', help='update tags in audio files')
  parser.add_argument('-c', '--clean-tags', action='store_true', help='clean tags in audio files')
  parser.add_argument('-a', '--ask', action='store_true', help='print info and ask user')
  parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
  parser.add_argument('--save-db', help='save tags to database', default='tracks.db')
  parser.add_argument('--load-db', help='load tags from database', default='tracks.db')
  return parser

if __name__ == "__main__": 
  # input parser
  input_parser = argsParserInit()
  args = input_parser.parse_args()

  # args chech
  if (len(sys.argv) <= 1):
    input_parser.print_help()  
    sys.exit(0)

  # scan for flac files
  beatport_id_pattern = re.compile('^[0-9]+[_]')
  flac_files = Track.scanFiles()

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
    for track in Track.database:
      track.fileTagsUpdate()

  # clean file tags
  if args.clean_tags:
    for file in flac_files:
      Track.cleanTags(file)

  print('Done')

  #x = input()

  #tr.getTags()
  #tr.fileTagsUpdate(Track.scanFiles().pop())

  #print(Track.scanFiles())

  #tr.printTrackInfo()

  #audio = FLAC("data/3058620_Cruoris_Civilis_Original_Mix.flac")
