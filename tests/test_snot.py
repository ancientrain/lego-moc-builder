"""SNOT / side-connection regression tests.

Run with:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, "scripts"))

import check  # noqa: E402
from ldrawlib import Library  # noqa: E402
from model import Model  # noqa: E402
from orientation import apply, orientation_for_stud  # noqa: E402
from paths import find_ldraw  # noqa: E402


class SnotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = Library(find_ldraw())

    def test_orientation_for_side_stud(self):
        m = orientation_for_stud((0, 0, -1))
        self.assertEqual(apply(m, (0, 1, 0)), (0, 0, 1))   # socket faces host
        self.assertEqual(apply(m, (0, -1, 0)), (0, 0, -1))  # top faces out

    def test_body_bbox_excludes_side_stud(self):
        body = self.lib.body_bbox("87087")
        full = self.lib.geometry("87087")[1]
        self.assertEqual(body[2], -10.0)   # body front
        self.assertEqual(full[2], -14.0)   # side stud sticks out 4 LDU

    def test_11211_has_two_side_studs(self):
        studs = self.lib.studs("11211")
        side = [n for _p, n in studs if n[2] < -0.9]
        self.assertEqual(len(side), 2)

    def test_place_on_stud_is_connected(self):
        m = Model(self.lib, 10, 8)
        m.place("3020", 10, 0, 0, 0)
        host = m.place("11211", 14, 2, 0, 1)
        tile = m.place_on_stud("3070b", 0, host, 0)
        self.assertTrue(tile.snot)
        self.assertEqual(tile.cells, [])
        self.assertEqual(m.occ.get((2, 0, 1)), host)
        self.assertNotIn(tile, m.occ.values())
        r = check.report(m)
        self.assertEqual(r["floating"], [])
        self.assertEqual(r["orphans"], [])
        self.assertEqual(r["snot_parts"], 1)
        self.assertGreaterEqual(r["connections"], 2)
        self.assertIn("0 0 -1 0 1 0", m.placement_line(tile))

    def test_unattached_snot_is_reported(self):
        m = Model(self.lib, 10, 8)
        m.place("3020", 10, 0, 0, 0)
        m.place("11211", 14, 2, 0, 1)
        m.place("3070b", 0, 8, 1, 1, rot=(90, 0, 0), strict=False)
        # a free-standing vertical tile is not connected to anything
        r = check.report(m)
        self.assertEqual(len(r["snot_unsupported"]), 1)


if __name__ == "__main__":
    unittest.main()
