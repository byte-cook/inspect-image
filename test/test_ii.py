#!/usr/bin/env python3

import unittest
import os
import io
import sys
import re
import shutil
import datetime
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

# import from parent dir
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(PROJECT_DIR))
import ii
ROOT_DIR = os.path.join(PROJECT_DIR, 'root')
IMAGE_DIR = os.path.join(ROOT_DIR, 'image')

# Usage:
# > test_ii.py
# > test_ii.py TestII.test_clean

class TestII(unittest.TestCase):
    def setUp(self):
        os.makedirs(ROOT_DIR, exist_ok=True)
        shutil.rmtree(ROOT_DIR)
        os.makedirs(IMAGE_DIR, exist_ok=True)
   
    def test_check_image(self):
        print('======= test_check_image ===')
        a1 = os.path.join(IMAGE_DIR, 'Artist 1/Album One')
        os.makedirs(a1, exist_ok=True)
        self._createFiles(a1, 5)
        a2 = os.path.join(IMAGE_DIR, 'Artist 2/Album Two')
        os.makedirs(a2, exist_ok=True)
        self._createFiles(a2, 5)
        with patch('sys.stdout', new = io.StringIO()) as mock_out:
            ii.main(['-l', 'mp3', IMAGE_DIR])
        outputLines = mock_out.getvalue().splitlines()
        print(mock_out.getvalue())
        self.assertEqual(len(outputLines), 0)

    def test_check_image_witherror(self):
        print('======= test_check_image_witherror ===')
        a1 = os.path.join(IMAGE_DIR, 'Artist 1/Album One')
        os.makedirs(a1, exist_ok=True)
        self._createFiles(a1, 2)
        self._createFiles(a1, 2, postfix='NExt', startIndex=2)
        self._createFiles(a1, 1, postfix='space ', startIndex=4)
        self._createFiles(a1, 1, postfix='a  double space', startIndex=5)
        a2 = os.path.join(IMAGE_DIR, 'Artist 2/Album TWo')
        os.makedirs(a2, exist_ok=True)
        self._createFiles(a2, 5)
        self._createFiles(a2, 2, startIndex=7)
        with patch('sys.stdout', new = io.StringIO()) as mock_out:
            ii.main(['mp3', IMAGE_DIR])
        outputLines = mock_out.getvalue().splitlines()
        print(mock_out.getvalue())
        outputLines = self._assertLineAndRemove(outputLines, '.*'+'NExt'+'.*'+'Lower case required'+'.*', 2)
        outputLines = self._assertLineAndRemove(outputLines, '.*'+'Album TWo'+'.*'+'Start case required'+'.*', 7)
        outputLines = self._assertLineAndRemove(outputLines, '.*'+'8'+'.*'+'Illegal numbering'+'.*', 1)
        outputLines = self._assertLineAndRemove(outputLines, '.*'+'space'+'.*'+'Empty space at the end'+'.*', 1)
        outputLines = self._assertLineAndRemove(outputLines, '.*'+'a  double space'+'.*'+'Repeated spaces'+'.*', 1)
        self.assertEqual(len(outputLines), 0)
        
    def test_clean(self):
        print('======= test_clean ===')
        shutil.rmtree(ROOT_DIR)
    
    # Helper methods
    def _createFiles(self, dir, numberFiles=1, postfix='file', startIndex=0):
        os.makedirs(dir, exist_ok=True)
        for i in range(startIndex, startIndex+numberFiles):
            fileName = os.path.join(dir, f'{i+1}-{postfix}.mp3')
            with open(fileName, 'x') as f:
                pass
    
    def _assertLineAndRemove(self, outputLines, pattern, expectedCount):
        count = 0
        remainingLines = []
        for line in outputLines:
            result = re.search(pattern, line, re.IGNORECASE)
            if result:
                count += 1
            else:
                remainingLines.append(line)
        self.assertEqual(count, expectedCount, msg=f'Pattern "{pattern}" found {count} times')
        return remainingLines

if __name__ == '__main__':
    unittest.main()
    