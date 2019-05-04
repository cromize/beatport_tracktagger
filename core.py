import threading
import queue
import time
import json
import re

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
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
    tr.artists = f['ARTIST']
    tr.title = f['TITLE'].pop().split(' (')[0]
  except:
    print("** error cannot match file without artist or title")
    print("** skipping")
    return

  # try to extract remixer
  try:
    tr.remixer = f['TITLE'][0].split('(')[1].split(')')[0]
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
  # if is valid beatport file
  if beatport_id_pattern.match(filename):
    beatport_id = int(beatport_id_pattern.match(filename).group()[:-1])
    if db.trackInDB(beatport_id):
      processing_iterator += 1
      print(f'{processing_iterator}/{db.track_count} - (Already in DB) {filename}')
      return processing_iterator

    # create and get tags
    track = Track(beatport_id)
    track.file_path = Path(filepath)
    track.file_name = filename

    try:
      # if fail try fuzzyMatch
      for i in range(2):
        try:
          page = track.queryTrackPage()
          track.getTags(page)
          i = 2
        except Exception as ee:
          print("\n** beatport id is invalid")
          print("** trying using fuzzy matching")
          track = doFuzzyMatch(track.file_path, db)
          processing_iterator -= 1

      processing_iterator += 1
      db.db[track.beatport_id] = track
      print(f"{processing_iterator}/{db.track_count} - {track.file_path}") 
    except Exception as e:
      processing_iterator += 1
      print("** error cannot get track info!")
      print(f"{processing_iterator}/{db.track_count} - (Cannot get track info) {filename}") 
      return

# add beatport id using fuzzy matching
def doFuzzyMatch(f, db):
  global processing_iterator 
  buf = []
  processing_iterator += 1
  print(f"{processing_iterator}/{db.track_count} - (fuzzy matching) {f}")
  tr = scrapeFileTags(f)
  if tr:
    res = Track.queryTrackSearch(tr)
    match_id = Track.fuzzyTrackMatch(res, tr)
    tr.beatport_id = match_id
    db.db[match_id] = tr
    buf.append(f)
  return tr

