import mutagen
import urllib3
import sys

from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture, FLAC
from mutagen.id3 import ID3
from pathlib import Path
from lxml import html

http = urllib3.HTTPSConnectionPool("www.beatport.com", maxsize=20, cert_reqs='CERT_NONE', assert_hostname=False)

class Track:
  def __init__(self, beatport_id = 0):
    # filepath is assigned after being scanned
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

  # returns most probable match
  def fuzzyTrackMatch(src, template):
    from fuzzywuzzy import process
    from fuzzywuzzy.fuzz import token_sort_ratio
    template = " ".join(template.artists), template.title, template.remixer
    x = dict()
    # candidates in src
    for k, v in src.items():
      x[k] = " ".join((*v.artists, v.title, v.remixer))
    match = process.extractOne(" ".join(template), x, scorer=token_sort_ratio)
    return match[2]

  def queryTrackPage(self):
    try:
      page = http.request('GET', '/track/aa/' + str(self.beatport_id))
    except Exception as e:
      print(e)
      print(f"** error cannot get track info!")
      return
    return html.fromstring(page.data)

  # query track using beatport search engine
  def queryTrackSearch(track):
    from urllib import parse
    query = parse.quote(f"{' '.join(track.artists)} {track.title} {track.remixer}")
    page = http.request('GET', f'/search/tracks?per-page=20&q={query}&page=1')
    page_count = len(html.fromstring(page.data).xpath('//*[@id="pjax-inner-wrapper"]/section/main/div/div[3]/div[3]/div[1]/div/*'))
    if page_count == 0:
      page_count = 1

    # should we query all pages? desired result should be at first page if relevant
    # 20 per-page
    tracks = dict()
    rtracks = html.fromstring(page.data).xpath('//*[@id="pjax-inner-wrapper"]/section/main/div/div[3]/ul/*')
    
    # for every track in result page
    for rtrack in rtracks:
      track = Track(0)
      rartists = []
      rartists_cont = rtrack.find_class("buk-track-artists").pop()
      # get all artists of track
      for it in rartists_cont.iterchildren():
        rartists.append(it.text)
      # assign tags into new Track object
      track.artists = rartists
      track.title = rtrack.find_class("buk-track-primary-title").pop().text
      track.remixer = rtrack.find_class("buk-track-remixed").pop().text
      track.beatport_id = int(rtrack.get('data-ec-id'))
      tracks[track.beatport_id] = track
    return tracks

  # get tags using beatport id
  def getTags(self, page):
    artistCount = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/div[1]/span[2]/a')
    artistCount = len(artistCount)

    # could be more artists
    for artist in range(1, artistCount + 1):
      path = page.xpath(f'//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/div[1]/span[2]/a[{str(artist)}]/text()')
      self.artists.append(path.pop())

    # get info from beatport
    self.title = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[1]/div[1]/h1[1]/text()').pop()
    self.remixer = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[1]/div[1]/h1[2]/text()').pop()
    self.length = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[1]/span[2]/text()').pop()
    self.released = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[2]/span[2]/text()').pop()
    self.bpm = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[3]/span[2]/text()').pop()
    self.key = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[4]/span[2]/text()').pop()
    self.genre = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[5]/span[2]/a/text()').pop()
    self.label = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[2]/li[6]/span[2]/a/text()').pop()
    self.album = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[1]/li/@data-ec-name').pop()
    self.artwork_url = page.xpath('//*[@id="pjax-inner-wrapper"]/section/main/div[2]/div/ul[1]/li/a/img').pop().attrib['src']

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
    dl_img = urllib3.PoolManager(cert_reqs='CERT_NONE', assert_hostname=False).request('GET', self.artwork_url).data
    if Path(self.file_name).suffix == ".flac":
      audiof = FLAC(self.file_path)  
      img = Picture()
      img.type = 3
      img.desc = 'artwork'
      img.data = dl_img
      audiof.add_picture(img)
    elif Path(self.file_name).suffix == ".mp3":
      audiof = ID3(self.file_path)  
      audiof.add(mutagen.id3.APIC(3, 'image/jpeg', 3, 'Front cover', dl_img))
    audiof.save()

  def cleanTags(filepath):
    if Path(filepath).suffix == ".flac":
      audiof = FLAC(filepath)  
      audiof.clear_pictures()
      audiof.delete()
    elif Path(filepath).suffix == ".mp3":
      audiof = EasyID3(filepath)  
      audiof.delete()
    audiof.save()
