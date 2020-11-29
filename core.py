import threading
import queue
import time
import json
import re

from fuzzywuzzy.fuzz import token_sort_ratio
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from unidecode import unidecode
from pathlib import Path
from track import Track

MAX_WORKERS = 10

beatport_id_pattern = re.compile('^[0-9]+[_]')
processing_iterator = 0

def scrapeFileTags(path):
  if path.suffix == ".flac":
    f = FLAC(path)  
  elif path.suffix == ".mp3":
    f = EasyID3(path)  

  tr = Track(0)
  tr.file_name = path.name
  tr.file_path = path

  # extract artist and title
  try:
    tr.artists = f['ARTIST'] or f['artist']
    tr.title = f['TITLE'].pop().split(' (')[0] or f['title'].pop().split(' (')[0]
  except:
    print("*** error cannot match file without artist or title")
    print(f"*** skipping {path.name}")
    return

  # try to extract remixer
  try:
    tr.remixer = f['TITLE'][0].split('(')[1].split(')')[0] or f['title'][0].split('(')[1].split(')')[0]
  except:
    # assume it's original mix, when no remixer is supplied
    tr.remixer = "Original Mix"
  return tr

# return valid filetypes only
def scanFiletype(src, recursive):
  filetypes = '.flac', '.mp3'
  if Path(src).is_file():           # single file
    files = {Path(src)}
  elif recursive:                   # recursive 
    files = Path(src).glob('**/*')
  else:                             # input folder
    files = Path(src).glob('*')     

  # match filetype
  out = set() 
  for f in files:
    if Path(f).suffix in filetypes: 
      out.add(f)
  return out

# *** database ***

class Database:
  def __init__(self):
    # from file scan
    self.track_count = 0
    self.db = dict()

  # get path of scanned files with beatport id in filename
  def scanBeatportID(self, files):
    outputFiles = []
    for f in files:
      # match beatport id in Track.db
      if beatport_id_pattern.match(Path(f).name):
        beatport_id = int(beatport_id_pattern.match(Path(f).name).group()[:-1])
        if beatport_id in self.db.keys():
          # assing scanned path to db
          self.db[beatport_id].file_path = Path(f)
        # do we want to append files that are not in db?
        outputFiles.append(Path(f))
    self.track_count = len(outputFiles)
    return outputFiles

  def assignPath(self, files):
    outputFiles = []
    for f in files:
      for k,v in self.db.items():
        if Path(f).name == v.file_name:
          self.db[k].file_path = Path(f)
          outputFiles.append(Path(f))
    self.track_count = len(outputFiles)
    return outputFiles

  def trackInDB(self, beatport_id):
    if beatport_id in self.db:
      return True
    return False
    
  def loadJSON(self, src):
    json_db = []
    with open(src, 'r') as f:
      json_db = f.readlines()
    for track in json_db:
      track_object = Track()
      track_object.__dict__ = json.loads(track)
      self.db[track_object.beatport_id] = track_object

  def saveJSON(self, src):
    with open(src, 'w') as f:
      for k, v in self.db.items():
        import copy                      # raw object copy, to make true duplicate
        vv = copy.copy(v) 
        if "file_path" in vv.__dict__:
          del vv.__dict__["file_path"]   # we won't store file_path
        track_json = json.dumps(vv.__dict__)
        f.write(track_json + '\n')

# *** thread-safe ***

def spawnWorkers(method, data, arg=None):
  global processing_iterator 
  processing_iterator = 0
  q = queue.Queue()
  threads = []
  for i in range(MAX_WORKERS):
    t = threading.Thread(target=worker, args=(method,q,arg))
    t.start()
    threads.append(t)

  for f in data:
    q.put(f) 

  # wait for workers
  q.join()
  
  # kill workers
  for i in range(MAX_WORKERS):
    q.put(None)
  for t in threads:
    t.join() 

def worker(work, queue, arg=None):
  while True:
    item = queue.get()
    if item is None:
      break
    work(item, arg)
    queue.task_done()

def addTrackToDB(filepath, db):
  global processing_iterator 
  filename = Path(filepath).name

  # don't query if in database
  for k,v in db.db.items():
    if v.file_name == Path(filepath).name:
      processing_iterator += 1
      print(f"{processing_iterator}/{db.track_count} - (already in DB) {Path(filepath).name}")
      return v

  # if is valid beatport file
  if beatport_id_pattern.match(filename):
    beatport_id = int(beatport_id_pattern.match(filename).group()[:-1])
    if db.trackInDB(beatport_id):
      processing_iterator += 1
      print(f'{processing_iterator}/{db.track_count} - (already in DB) {filename}')
      return processing_iterator

    # create and get tags
    track = Track(beatport_id)
    track.file_path = Path(filepath)
    track.file_name = filename

    try:
      page = track.queryTrackPage()
      track.getTags(page)
    except Exception as ee:
      processing_iterator += 1
      print(f"{processing_iterator}/{db.track_count} - {filename}")
      print("*** beatport id is invalid")
      print("*** try to use fuzzy matching (-z)\n")
      return

    processing_iterator += 1
    db.db[track.beatport_id] = track
    print(f"{processing_iterator}/{db.track_count} - {track.file_name}") 
    return

# add beatport id using fuzzy matching
def doFuzzyMatch(f, db):
  global processing_iterator 
  processing_iterator += 1

  # don't query if in database
  for k,v in db.db.items():
    if v.file_name == Path(f).name:
      print(f"{processing_iterator}/{db.track_count} - (already in DB) {f}")
      return v

  print(f"{processing_iterator}/{db.track_count} - (fuzzy matching) {f}")

  tr = scrapeFileTags(f)
  scraped_info = (unidecode(tr.artists[0].lower()), tr.title)
  if tr:
    res = Track.queryTrackSearch(tr)
    if not res:
      print(f"*** NO match for {f}")
      return tr
    match_id = Track.fuzzyTrackMatch(res, tr)
    if not match_id:
      print(f"*** NO match for {f}")
      return tr
    tr.beatport_id = match_id

    # get tags
    page = tr.queryTrackPage()
    tr.getTags(page)

    # check if track title and artists really match our query
    queried_info = ([unidecode(x.lower()) for x in tr.artists], tr.title)
    title_prob = token_sort_ratio(scraped_info[1], queried_info[1])
    if scraped_info[0] not in queried_info[0] or title_prob <= 80:
      print(f"*** NO match for {f}")
      return tr

    db.db[match_id] = tr
  return tr

