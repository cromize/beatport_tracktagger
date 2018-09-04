#!/usr/bin/env python3

import requests
import json
import mutagen
import glob
import re

from lxml import html
from mutagen.flac import FLAC

class Track:
  json_database = []
  database = []

  def __init__(self, beatport_id = 0):
    self.beatport_id = beatport_id

    self.artists = []
    self.title = 'N/A'
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

  def printTrackInfo(self):
    print ('Track: ', end='')

    x = 1
    for artist in self.artists:
      print (artist, end='')
      if len(self.artists) > 1 and x < len(self.artists):
        print (', ', end='')
      x += 1

    print (f' - {self.title} ({self.remixer})')
    print (f'Length: {self.length}\n'
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
    count = 0

    # For wavs only
    for f in files:
      file_path = f
      # win
      f = f.split('\\')[-1]
      # linux 
      f = f.split('/')[-1]

      if f.lower().endswith(filetypes):
        if beatport_id_pattern.match(f):
          outputFiles.append(file_path)
          count += 1

    return outputFiles

  def trackInDB(beatport_id):
    for track in Track.database:
      if track.beatport_id == beatport_id: return True

    return False

  def fileTagsUpdate(self, path):
    file = FLAC(path)  

    if len(self.artists) == 1: file['ARTIST'] = self.artists
    else:
      temp = ""
      count = 0

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

    print(file.pprint())
    file.save()
    

if __name__ == "__main__": 
  beatport_id_pattern = re.compile('^[0-9]+[_]')
  tr = Track("1839527")
  #tr.getTags()
  tr.fileTagsUpdate(Track.scanFiles().pop())

  #print(Track.scanFiles())

  #tr.printTrackInfo()

  #audio = FLAC("data/3058620_Cruoris_Civilis_Original_Mix.flac")
