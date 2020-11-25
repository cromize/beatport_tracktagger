#!/usr/bin/env python3
import unittest
import urllib3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core

from mutagen.flac import FLAC
from pathlib import Path

def filedir():
  return Path(__file__).resolve().parent

class TestTrackTagger(unittest.TestCase):
  def test_flac_scrapeFileTags(self):
    tr = core.scrapeFileTags(filedir()/'data/9348620_take_care.flac')
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.file_path, filedir()/'data/9348620_take_care.flac')
    self.assertEqual(tr.file_name, '9348620_take_care.flac')
  
  def test_mp3_scrapeFileTags(self):
    tr = core.scrapeFileTags(filedir()/'data/5850811_2090.mp3')
    self.assertEqual(tr.artists, ['Alex Okrazo'])
    self.assertEqual(tr.title, '2090')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.file_path, filedir()/'data/5850811_2090.mp3')
    self.assertEqual(tr.file_name, '5850811_2090.mp3')

  def test_scanFiletype(self):
    files = core.scanFiletype(filedir()/'data/', False)
    self.assertEqual(files, {filedir()/'data/9348620_take_care.flac', filedir()/'data/5850811_2090.mp3'})

    # recursive
    files = core.scanFiletype(filedir(), True)
    self.assertEqual(files, {filedir()/'data/9348620_take_care.flac', filedir()/'data/5850811_2090.mp3'})

  def test_addTrackToDB(self):
    db = core.Database()
    core.addTrackToDB(filedir()/'data/9348620_take_care.flac', db)

    tr = db.db[9348620] 
    self.assertEqual(tr.beatport_id, 9348620)
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.album, 'Remixes Compilation VOL02')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.released, '2017-06-05')
    self.assertEqual(tr.bpm, 126)
    self.assertEqual(tr.genre, 'Techno (Peak Time / Driving)')
    self.assertEqual(tr.label, 'Dolma Records')
    self.assertEqual(tr.catalog, 'DM098')
    
  def test_scanBeatportID(self):
    f = Path(filedir()/'data/9348620_take_care.flac')
    db = core.Database()
    core.addTrackToDB(f, db)
    db.scanBeatportID([f])

    self.assertEqual(db.db[9348620].file_path, filedir()/'data/9348620_take_care.flac')

  def test_doFuzzyMatch(self):
    # 5945839 and 9348620 are the same
    f = Path(filedir()/'data/9348620_take_care.flac')
    db = core.Database()
    core.doFuzzyMatch(f, db)

    tr = db.db[5945839] 
    self.assertEqual(tr.beatport_id, 5945839)
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')

  def test_flac_fileTagsUpdate(self):
    f = Path(filedir()/'data/9348620_take_care.flac')
    db = core.Database()
    core.addTrackToDB(f, db)

    tr = db.db[9348620]
    tr.fileTagsUpdate(force=True)

    audiof = FLAC(tr.file_path)
    self.assertEqual(audiof['ARTIST'], ['Ronny Vergara'])
    self.assertEqual(audiof['DATE'], ['2017'])  # we save only year into the file
    self.assertEqual(audiof['GENRE'], ['Techno (Peak Time / Driving)'])
    self.assertEqual(audiof['ORGANIZATION'], ['Dolma Records'])
    self.assertEqual(audiof['TITLE'], ['Take Care (Hackler & Kuch Remix)'])
    self.assertEqual(audiof['ALBUM'], ['Remixes Compilation VOL02'])
    self.assertEqual(audiof['BPM'], ['126'])

if __name__ == '__main__':
  unittest.main()
