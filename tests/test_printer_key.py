"""A printer key names one baked profile and nothing else.

Standard library only, like the engine: python3 -m unittest discover tests
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'engine'))
import gui
import optimise3mf

# engine/data/index.json exists, so '../index' opens a real file unless refused
BAD = ('../index', '../../README', '/etc/hostname', 'u1/../../index', '')


class PrinterKey(unittest.TestCase):
    def test_a_real_key_still_loads(self):
        key = gui.printers()[0]['key']
        self.assertTrue(gui.settings_for(key)['rows'])
        self.assertIn('label', optimise3mf.load_printer(key))

    def test_the_window_never_reads_outside_the_printer_data(self):
        for bad in BAD:
            self.assertEqual(gui.settings_for(bad), {'rows': []}, bad)

    def test_the_engine_never_reads_outside_the_printer_data(self):
        for bad in BAD:
            with self.assertRaises(SystemExit, msg=bad):
                optimise3mf.load_printer(bad)


if __name__ == '__main__':
    unittest.main()
