"""Served mode: the window run from a container rather than a desktop.

Standard library only, like the engine: python3 -m unittest discover tests
"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'engine'))
import gui


class ServeConfig(unittest.TestCase):
    def test_desktop_default_is_loopback_on_a_free_port(self):
        cfg = gui.serve_config({})
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('127.0.0.1', 0, False))

    def test_port_in_the_environment_turns_served_mode_on(self):
        cfg = gui.serve_config({'PRISM_HOST': '0.0.0.0', 'PRISM_PORT': '8096'})
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('0.0.0.0', 8096, True))

    def test_the_printed_address_uses_the_port_published_on_the_host(self):
        cfg = gui.serve_config({'PRISM_PORT': '8096', 'PRISM_PUBLIC_PORT': '9001'})
        self.assertEqual((cfg['port'], cfg['public_port']), (8096, 9001))
        self.assertEqual(gui.serve_config({'PRISM_PORT': '8096'})['public_port'], 8096)

    def test_a_port_that_is_not_a_port_is_refused(self):
        with self.assertRaises(SystemExit):
            gui.serve_config({'PRISM_PORT': '8096', 'PRISM_PUBLIC_PORT': 'x'})
        for bad in ('http', '0', '70000', '-1'):
            with self.assertRaises(SystemExit):
                gui.serve_config({'PRISM_PORT': bad})


class WorkFiles(unittest.TestCase):
    def test_lists_sources_and_leaves_out_what_prism_already_wrote(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('benchy.3mf', 'Vase.3MF', 'benchy - U1.3mf',
                         'benchy - VORON24-300.3mf', 'notes.txt'):
                open(os.path.join(d, name), 'w').close()
            got = [os.path.basename(p) for p in gui.work_files(d, ['U1', 'VORON24-300'])]
        self.assertEqual(got, ['Vase.3MF', 'benchy.3mf'])

    def test_a_name_that_only_looks_like_an_output_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, 'lid - final.3mf'), 'w').close()
            got = [os.path.basename(p) for p in gui.work_files(d, ['U1'])]
        self.assertEqual(got, ['lid - final.3mf'])

    def test_a_missing_folder_is_empty_not_an_error(self):
        self.assertEqual(gui.work_files('/nonexistent/prism-work', ['U1']), [])


if __name__ == '__main__':
    unittest.main()
