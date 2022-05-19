# -*- coding: utf-8 -*-
"""Manage access to image data."""

import configparser
import csv
import random

from lib.config import *


class Wordle:
    def __init__(self, word, wordlist, n=6):
        self.word = word
        self.n = 6
        self.wordlist = wordlist
        self.correct = [" " for i in range(len(word))]
        self.wrong_position = set()
        self.not_in_word = set()

    @property
    def remaining(self):
        return set(self.word) - set(self.correct)

    def __len__(self):
        return len(self.word)

    def user_won(self):
        if self.word == "".join(self.correct):
            return True
        return False

    def good_guess(self, guess):
        with open(self.wordlist) as infile:
            for line in infile:
                if line.strip().lower() == guess.lower():
                    return True
        return False

    def guess(self, guess):    
        # first pass, we look for correct letters
        for i, letter in enumerate(guess):
            if letter == self.word[i]:
                self.correct[i] = letter

        for i, letter in enumerate(guess):
            if letter in self.remaining:
                self.wrong_position.add(letter)
            
            else:
                if letter not in self.word:
                    self.not_in_word.add(letter)

        self.n -= 1


class ImageData(dict):
    """Manage the access to image data.

    Mapping from room id to items left for this room.

    Args:
        path (str): Path to a valid csv file with two columns
            per row, containing the url of two paired up
            images.
        n (int): Number of images presented per
            participant per room.
        shuffle (bool): Whether to randomly sample images or
            select them one by one as present in the file.
            If more images are present than required per room
            and participant, the selection is without replacement.
            Otherwise it is with replacement.
        seed (int): Use together with shuffle to
            make the image presentation process reproducible.
    """
    def __init__(self, path=None, n=1, shuffle=False, seed=None):
        self._path = path
        self._n = n
        self._shuffle = shuffle

        self._images = None
        if seed is not None:
            random.seed(seed)

    @property
    def n(self):
        return self._n

    def get_image_pairs(self, room_id):
        """Create a collection of image pair items.

        Each pair holds two url each to one image
        ressource. The image will be loaded from there.
        For local testing, you can host the images with python:
        ```python -m SimpleHTTPServer 8000```

        This functions remembers previous calls to itself,
        which makes it possible to split a file of items over
        several participants even for not random sampling.

        Args:
            room_id (str): Unique identifier of a task room.

        Returns:
            None
        """
        if self._images is None:
            # first time accessing the file
            # or a new access for each random sample
            self._images = self._image_gen()
        sample = []
        while len(sample) < self._n:
            try:
                word, image = next(self._images)
            except StopIteration:
                # we reached the end of the file
                # and start again from the top
                self._images = self._image_gen()
            else:
                sample.append(tuple((Wordle(word, WORD_LIST), image)))
        if self._shuffle:
            pass
            # # implements reservoir sampling
            # for img_line, img in enumerate(self._images, self._n):
            #     rand_line = random.randint(0, img_line)
            #     if rand_line < self._n:
            #         sample[rand_line] = tuple(img)
            # self._images = None
        self[room_id] = sample

    def _image_gen(self):
        """Generate one image pair at a time."""
        with open(self._path, 'r') as infile:
            for line in infile:
                word, link = line.strip().split("\t")
                yield word, link


if __name__ == "__main__":
    import os
    import sys
    import unittest

    im = ImageData(path="wordle/data/image_data.csv", n=3)
    breakpoint()

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(ROOT)

    from tests.test_image_data import TestImageData

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestImageData))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
