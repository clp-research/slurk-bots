# -*- coding: utf-8 -*-

# University of Potsdam
"""ImageData class test cases."""

import functools
import os
import sys
import unittest
from unittest import mock

from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from lib.image_data import ImageData


def file_mock(func):
    """Create pseudo file object."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        content = '\n'.join(f"{i},{i}" for i in range(6))
        with mock.patch('lib.image_data.open',
                        mock.mock_open(read_data=content)) as f_mock:
            func(*args, **kwargs)
    return wrapper


class TestImageData(unittest.TestCase):
    @file_mock
    def setUp(self):
        ImageData.items = dict()
        # not shuffled image data access
        self.not_shuffled = ImageData(path="", n=3)
        self.not_shuffled.get_image_pairs("mock_room")
        self.not_shuffled.get_image_pairs("other_mock_room")
        self.not_shuffled.get_image_pairs("another_mock_room")
        # shuffled image data access
        self.shuffled = ImageData(path="", n=3, shuffle=True, seed=24)
        self.shuffled.get_image_pairs("shuffled_mock_room")

    def test_not_shuffled_correct_order(self):
        expected_first_sample = [('0', '0'), ('1', '1'), ('2', '2')]
        expected_second_sample = [('3', '3'), ('4', '4'), ('5', '5')]
        actual_first_sample = self.not_shuffled["mock_room"]
        actual_second_sample = self.not_shuffled["other_mock_room"]

        self.assertEqual(actual_first_sample, expected_first_sample)
        self.assertEqual(actual_second_sample, expected_second_sample)

    def test_not_shuffled_sum_of_sample_sizes_exceeds_file_lines(self):
        # algorithm should start again from the beginning of the file
        expected = [('0', '0'), ('1', '1'), ('2', '2')]
        actual = self.not_shuffled["another_mock_room"]

        self.assertEqual(actual, expected)

    def test_shuffled_no_duplicates(self):
        expected = 3
        actual = len(set(self.shuffled["shuffled_mock_room"]))

        self.assertEqual(actual, expected)

    @file_mock
    def test_shuffled_reproducible(self):
        self.other_shuffled = ImageData(path="", n=3, shuffle=True, seed=24)
        self.other_shuffled.get_image_pairs("other_shuffled_mock_room")
        
        self.assertEqual(self.shuffled["shuffled_mock_room"],
                         self.other_shuffled["other_shuffled_mock_room"])

    @file_mock
    def test_shuffled_uniform_distribution(self):
        observations = dict()
        # create 200 rooms of size 3 (=600 data points)
        for i in range(200):
            self.shuffled.get_image_pairs(str(i))
            for item, _ in self.shuffled[str(i)]:
                if item not in observations:
                    observations[item] = 0
                observations[item] += 1
        # null hypothesis -> the sample is uniformly distributed
        likelihood_under_H0 = stats.chisquare(list(observations.values())).pvalue

        self.assertGreater(likelihood_under_H0, 0.50)


if __name__ == '__main__':
    unittest.main()
