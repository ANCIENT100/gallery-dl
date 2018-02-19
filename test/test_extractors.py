#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2015-2018 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import sys
import unittest
from gallery_dl import extractor, job, config, exception


SKIP = {
    # don't work on travis-ci
    "exhentai", "kissmanga", "mangafox", "dynastyscans", "nijie",
    "archivedmoe", "archiveofsins", "thebarchive",

    # temporary issues
    "chronos",
    "coreimg",
    "hosturimage",
    "imgtrex",
    "yeet",
}


class TestExtractors(unittest.TestCase):

    def setUp(self):
        name = "gallerydl"
        email = "gallerydl@openaliasbox.org"
        config.set(("cache", "file"), ":memory:")
        config.set(("downloader", "part"), False)
        config.set(("extractor", "username"), name)
        config.set(("extractor", "password"), name)
        config.set(("extractor", "nijie", "username"), email)
        config.set(("extractor", "seiga", "username"), email)
        config.set(("extractor", "tumblr", "api-key"),
                   "0cXoHfIqVzMQcc3HESZSNsVlulGxEXGDTTZCDrRrjaa0jmuTc6")

    def tearDown(self):
        config.clear()

    def _run_test(self, extr, url, result):
        if result:
            if "options" in result:
                for key, value in result["options"]:
                    config.set(key.split("."), value)
            content = "content" in result
        else:
            content = False

        tjob = job.TestJob(url, content=content)
        self.assertEqual(extr, tjob.extractor.__class__)

        if not result:
            return
        if "exception" in result:
            self.assertRaises(result["exception"], tjob.run)
            return

        try:
            tjob.run()
        except exception.HttpError as exc:
            try:
                if 500 <= exc.args[0].response.status_code < 600:
                    self.skipTest(exc)
            except AttributeError:
                pass
            raise

        # test archive-id uniqueness
        self.assertEqual(len(set(tjob.list_archive)), len(tjob.list_archive))

        # test extraction results
        if "url" in result:
            self.assertEqual(result["url"], tjob.hash_url.hexdigest())

        if "content" in result:
            self.assertEqual(result["content"], tjob.hash_content.hexdigest())

        if "keyword" in result:
            keyword = result["keyword"]
            if isinstance(keyword, dict):
                for kwdict in tjob.list_keyword:
                    self._test_kwdict(kwdict, keyword)
            else:  # assume SHA1 hash
                self.assertEqual(keyword, tjob.hash_keyword.hexdigest())

        if "count" in result:
            count = result["count"]
            if isinstance(count, str):
                self.assertRegex(count, r"^ *(==|!=|<|<=|>|>=) *\d+ *$")
                expr = "{} {}".format(len(tjob.list_url), count)
                self.assertTrue(eval(expr), msg=expr)
            else:  # assume integer
                self.assertEqual(len(tjob.list_url), count)

        if "pattern" in result:
            for url in tjob.list_url:
                self.assertRegex(url, result["pattern"])

    def _test_kwdict(self, kwdict, tests):
        for key, test in tests.items():
            if key.startswith("?"):
                key = key[1:]
                if key not in kwdict:
                    continue
            self.assertIn(key, kwdict)
            value = kwdict[key]

            if isinstance(test, dict):
                self._test_kwdict(kwdict[key], test)
                continue
            elif isinstance(test, type):
                self.assertIsInstance(value, test)
            elif isinstance(test, str) and value.startswith("re:"):
                self.assertRegex(value, test[3:])
            else:
                self.assertEqual(value, test)


def generate_tests():
    """Dynamically generate extractor unittests"""
    def _generate_test(extr, tcase):
        def test(self):
            url, result = tcase
            print("\n", url, sep="")
            self._run_test(extr, url, result)
        return test

    # enable selective testing for direct calls
    if __name__ == '__main__' and len(sys.argv) > 1:
        if sys.argv[1].lower() == "all":
            extractors = extractor.extractors()
        else:
            extractors = [
                extr for extr in extractor.extractors()
                if extr.category in sys.argv or
                hasattr(extr, "basecategory") and extr.basecategory in sys.argv
            ]
        del sys.argv[1:]
    else:
        extractors = [
            extr for extr in extractor.extractors()
            if extr.category not in SKIP
        ]

    for extr in extractors:
        if not hasattr(extr, "test") or not extr.test:
            continue
        name = "test_" + extr.__name__ + "_"
        for num, tcase in enumerate(extr.test, 1):
            test = _generate_test(extr, tcase)
            test.__name__ = name + str(num)
            setattr(TestExtractors, test.__name__, test)


generate_tests()
if __name__ == '__main__':
    unittest.main(warnings='ignore')
