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
        cfg = gui.serve_config({'PRISM_HOST': '0.0.0.0', 'PRISM_PORT': '8196'})
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('0.0.0.0', 8196, True))

    def test_the_printed_address_uses_the_port_published_on_the_host(self):
        cfg = gui.serve_config({'PRISM_PORT': '8196', 'PRISM_PUBLIC_PORT': '9001'})
        self.assertEqual((cfg['port'], cfg['public_port']), (8196, 9001))
        self.assertEqual(gui.serve_config({'PRISM_PORT': '8196'})['public_port'], 8196)

    def test_a_port_that_is_not_a_port_is_refused(self):
        with self.assertRaises(SystemExit):
            gui.serve_config({'PRISM_PORT': '8196', 'PRISM_PUBLIC_PORT': 'x'})
        for bad in ('http', '0', '70000', '-1'):
            with self.assertRaises(SystemExit):
                gui.serve_config({'PRISM_PORT': bad})


class PlainAddress(unittest.TestCase):
    """http://127.0.0.1:8196/ is what a person types, so it has to open."""
    served = {'served': True, 'public_port': 8196}

    def test_a_loopback_name_on_the_published_port_is_let_in(self):
        for host in ('127.0.0.1:8196', 'localhost:8196', '[::1]:8196', 'LOCALHOST:8196'):
            self.assertTrue(gui.is_local_visit(host, self.served), host)

    def test_a_rebinding_page_arrives_under_its_own_name_and_is_refused(self):
        for host in ('evil.example:8196', '127.0.0.1.evil.example:8196',
                     '192.168.1.20:8196', '127.0.0.1:9999', '127.0.0.1', '', None):
            self.assertFalse(gui.is_local_visit(host, self.served), host)

    def test_the_desktop_window_never_hands_its_token_out(self):
        desktop = {'served': False, 'public_port': 0}
        self.assertFalse(gui.is_local_visit('127.0.0.1:8196', desktop))


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


class LiveHandler(unittest.TestCase):
    """The real handler over a real socket: a redirect with no length hangs an
    HTTP/1.1 client for ever, and nothing short of a request shows it."""

    def setUp(self):
        import http.server, threading
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), gui.Handler)
        self.port = self.srv.server_address[1]
        self._cfg = gui.CONFIG
        gui.CONFIG = {'served': True, 'public_port': self.port, 'port': self.port,
                      'host': '127.0.0.1', 'work': '/nonexistent'}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        gui.CONFIG = self._cfg
        self.srv.shutdown()
        self.srv.server_close()

    def get(self, path, host=None):
        import http.client
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.request('GET', path, headers={'Host': host or '127.0.0.1:%d' % self.port})
        r = c.getresponse()
        r.read()
        return r

    def test_the_plain_address_redirects_to_the_token_and_the_page_opens(self):
        r = self.get('/')
        self.assertEqual(r.status, 302)
        self.assertEqual(r.getheader('Location'), '/?t=' + gui.TOKEN)
        self.assertEqual(self.get(r.getheader('Location')).status, 200)

    def test_another_name_in_the_host_header_gets_no_token(self):
        r = self.get('/', host='evil.example:%d' % self.port)
        self.assertEqual(r.status, 403)
        self.assertIsNone(r.getheader('Location'))

    def test_the_api_still_wants_the_token(self):
        self.assertEqual(self.get('/api/printers').status, 403)
        self.assertEqual(self.get('/?t=wrong').status, 403)


if __name__ == '__main__':
    unittest.main()
