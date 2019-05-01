#!/usr/bin/env python3
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core

from pathlib import Path

def workdir():
  print(Path(__file__).resolve().parent)
  return Path(__file__).resolve().parent

class TestTrackTagger(unittest.TestCase):
  def test_flac_scrapeFileTags(self):
    tr = core.scrapeFileTags(str(workdir()/'data/9348620_take_care.flac'))
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.file_path, workdir()/'data/9348620_take_care.flac')
    self.assertEqual(tr.file_name, '9348620_take_care.flac')
  
  def test_mp3_scrapeFileTags(self):
    tr = core.scrapeFileTags(str(workdir()/'data/9348620_take_care.mp3'))
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.file_path, workdir()/'data/9348620_take_care.mp3')
    self.assertEqual(tr.file_name, '9348620_take_care.mp3')

  def test_scanFiletype(self):
    files = core.scanFiletype(str(workdir()/'data/'), False)
    self.assertEqual(files, [Path('tests/data/9348620_take_care.flac').resolve(), Path('tests/data/9348620_take_care.mp3').resolve()])

    # recursive
    files = core.scanFiletype(workdir()/'.', True)
    self.assertEqual(files, [Path('tests/data/9348620_take_care.flac').resolve(), Path('tests/data/9348620_take_care.mp3').resolve()])

  def test_addTrackToDB(self):
    db = core.Database()
    core.addTrackToDB(str(Path('data/9348620_take_care.flac').resolve()), db)

    tr = db.db['9348620'] 
    self.assertEqual(tr.beatport_id, '9348620')
    self.assertEqual(tr.artists, ['Ronny Vergara'])
    self.assertEqual(tr.title, 'Take Care')
    self.assertEqual(tr.album, 'Remixes Compilation VOL02')
    self.assertEqual(tr.remixer, 'Hackler & Kuch Remix')
    self.assertEqual(tr.released, '2017-06-05')
    self.assertEqual(tr.bpm, '126')
    self.assertEqual(tr.genre, 'Techno')
    self.assertEqual(tr.label, 'Dolma Records')
    
  def test_scanBeatportID(self):
    f = Path('data/9348620_take_care.flac')
    db = core.Database()
    core.addTrackToDB(f, db)
    db.scanBeatportID([f])

    self.assertEqual(db.db['9348620'].file_path, Path('data/9348620_take_care.flac'))
    
if __name__ == '__main__':
  unittest.main()
