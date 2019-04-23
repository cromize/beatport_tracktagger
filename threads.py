import threading
import queue

from pathlib import Path
from track import Track
from core import scrapeFileTags, beatport_id_pattern

# things here should be considered threadable

MAX_WORKERS = 20

processing_iterator = 0

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
    beatport_id = beatport_id_pattern.match(filename).group()[:-1]
    if db.trackInDB(beatport_id):
      processing_iterator += 1
      print(f'{processing_iterator}/{db.track_count} - (Already in DB) {filename}')
      return processing_iterator

    # create and get tags
    track = Track(beatport_id)
    track.file_path = str(Path(filepath))
    track.file_name = filename

    # try 10 times
    for tries in range(10):
      try:
        page = track.queryTrackPage()
        track.getTags(page)
        break
      except Exception as e:
        print(e)
        pass

    processing_iterator += 1
    db.db[track.beatport_id] = track
    print(f"{processing_iterator}/{db.track_count} - {track.file_name}") 

# add beatport id using fuzzy matching
def doFuzzyMatch(f, db):
  global processing_iterator 
  buf = []
  processing_iterator += 1
  print(f"{processing_iterator}/{db.track_count} - {f}")
  tr = scrapeFileTags(f)
  if tr:
    res = Track.queryTrackSearch(tr)
    match_id = Track.fuzzyTrackMatch(res, tr)
    tr.beatport_id = match_id
    db.db[match_id] = tr
    buf.append(f)

  return processing_iterator
