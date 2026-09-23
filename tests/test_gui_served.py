"""Served mode: the window run from a container rather than a desktop.

Standard library only, like the engine: python3 -m unittest discover tests
"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'engine'))
import gui


class ServeConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def served(self, **env):
        return gui.serve_config(dict(PRISM_SERVE='1', PRISM_WORK=self.work, **env))

    def quiet(self, env):
        import contextlib, io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cfg = gui.serve_config(env)
        return cfg, err.getvalue()

    def test_desktop_default_is_loopback_on_a_free_port(self):
        cfg = gui.serve_config({})
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('127.0.0.1', 0, False))

    def test_a_port_alone_no_longer_serves(self):
        cfg, err = self.quiet({'PRISM_PORT': '8196', 'PRISM_HOST': '0.0.0.0'})
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('127.0.0.1', 0, False))
        self.assertIn('PRISM_PORT, PRISM_HOST', err)

    def test_zero_or_empty_is_the_desktop_and_says_nothing(self):
        for off in ('', '0'):
            cfg, err = self.quiet({'PRISM_SERVE': off})
            self.assertEqual((cfg['served'], err), (False, ''), off)

    def test_the_switch_serves_on_the_default_port(self):
        cfg = self.served()
        self.assertEqual((cfg['host'], cfg['port'], cfg['public_port'], cfg['served']),
                         ('127.0.0.1', 8196, 8196, True))
        self.assertEqual(cfg['work'], os.path.realpath(self.work))

    def test_the_switch_with_a_port_and_host(self):
        cfg = self.served(PRISM_PORT='9001', PRISM_HOST='0.0.0.0')
        self.assertEqual((cfg['host'], cfg['port'], cfg['served']),
                         ('0.0.0.0', 9001, True))

    def test_a_switch_that_is_not_one_is_refused(self):
        for bad in ('true', 'yes', 'on', '2', ' 1', 'ture'):
            with self.assertRaises(SystemExit, msg=bad):
                gui.serve_config({'PRISM_SERVE': bad})

    def test_a_root_is_never_checked_on_the_desktop(self):
        cfg, _ = self.quiet({'PRISM_WORK': '/'})
        self.assertFalse(cfg['served'])

    def test_the_printed_address_uses_the_port_published_on_the_host(self):
        cfg = self.served(PRISM_PORT='8196', PRISM_PUBLIC_PORT='9001')
        self.assertEqual((cfg['port'], cfg['public_port']), (8196, 9001))
        self.assertEqual(self.served(PRISM_PORT='8196')['public_port'], 8196)

    def test_a_port_that_is_not_a_port_is_refused(self):
        with self.assertRaises(SystemExit):
            self.served(PRISM_PORT='8196', PRISM_PUBLIC_PORT='x')
        for bad in ('http', '0', '70000', '-1'):
            with self.assertRaises(SystemExit, msg=bad):
                self.served(PRISM_PORT=bad)


class WorkRoot(unittest.TestCase):
    """The one folder the served window may reach, fixed at start."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, 'root')
        os.makedirs(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_root_is_the_resolved_folder(self):
        link = os.path.join(self.tmp.name, 'link')
        os.symlink(self.root, link)
        self.assertEqual(gui.work_root(link), os.path.realpath(self.root))

    def test_a_relative_root_is_refused(self):
        for bad in ('work', './work', ''):
            with self.assertRaises(SystemExit, msg=bad):
                gui.work_root(bad)

    def test_a_missing_root_is_refused(self):
        with self.assertRaises(SystemExit):
            gui.work_root(os.path.join(self.tmp.name, 'nope'))

    def test_a_file_is_not_a_root(self):
        f = os.path.join(self.tmp.name, 'a.3mf')
        open(f, 'w').close()
        with self.assertRaises(SystemExit):
            gui.work_root(f)

    def test_the_whole_filesystem_is_refused(self):
        slash = os.path.join(self.tmp.name, 'slash')
        os.symlink('/', slash)
        for bad in ('/', '//', '/../', slash):
            with self.assertRaises(SystemExit, msg=bad):
                gui.work_root(bad)


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


class InsideRoot(unittest.TestCase):
    """Served, every file path the page sends is checked against the root."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, 'root')
        os.makedirs(os.path.join(self.root, 'models'))
        open(os.path.join(self.root, 'models', 'benchy.3mf'), 'w').close()
        open(os.path.join(self.tmp.name, 'outside.3mf'), 'w').close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_paths_inside_the_root_may_be_converted(self):
        inside = os.path.join(self.root, 'models', 'benchy.3mf')
        outside = os.path.join(self.tmp.name, 'outside.3mf')
        sneaky = os.path.join(self.root, 'models', '..', '..', 'outside.3mf')
        self.assertEqual(
            gui.inside_root(self.root, [inside, outside, sneaky, '/etc/passwd']),
            [inside])

    def test_a_link_out_of_the_root_is_outside(self):
        os.symlink(os.path.join(self.tmp.name, 'outside.3mf'),
                   os.path.join(self.root, 'models', 'escape.3mf'))
        self.assertEqual(gui.inside_root(
            self.root, [os.path.join(self.root, 'models', 'escape.3mf')]), [])

    def test_a_sibling_sharing_the_root_prefix_is_outside(self):
        work = os.path.join(self.tmp.name, 'work')
        os.makedirs(os.path.join(self.tmp.name, 'work2'))
        os.makedirs(work)
        sibling = os.path.join(self.tmp.name, 'work2', 'x.3mf')
        open(sibling, 'w').close()
        self.assertEqual(gui.inside_root(work, [sibling]), [])


class LiveHandler(unittest.TestCase):
    """The real handler over a real socket: a redirect with no length hangs an
    HTTP/1.1 client for ever, and nothing short of a request shows it."""

    def setUp(self):
        import http.server, threading
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), gui.Handler)
        self.port = self.srv.server_address[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.work = os.path.join(self.tmp.name, 'work')
        os.makedirs(self.work)
        self.outside = os.path.join(self.tmp.name, 'outside.3mf')
        open(self.outside, 'w').close()
        self._cfg, self._engine, self._reveal = gui.CONFIG, gui.engine, gui.reveal
        self.ran, self.revealed = [], []
        gui.engine = lambda args, timeout=900: self.ran.append(args) or (0, '[]', '')
        gui.reveal = self.revealed.append
        gui.CONFIG = {'served': True, 'public_port': self.port, 'port': self.port,
                      'host': '127.0.0.1', 'work': self.work}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        gui.CONFIG, gui.engine, gui.reveal = self._cfg, self._engine, self._reveal
        self.srv.shutdown()
        self.tmp.cleanup()
        self.srv.server_close()

    def get(self, path, host=None):
        import http.client
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.request('GET', path, headers={'Host': host or '127.0.0.1:%d' % self.port})
        r = c.getresponse()
        r.read()
        c.close()
        return r

    def post(self, path, body):
        import http.client, json
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.request('POST', path + '?t=' + gui.TOKEN, body=json.dumps(body),
                  headers={'Host': '127.0.0.1:%d' % self.port,
                           'Content-Type': 'application/json'})
        r = c.getresponse()
        r.read()
        c.close()
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

    def test_a_path_outside_the_root_never_reaches_the_engine(self):
        inside = os.path.join(self.work, 'a.3mf')
        open(inside, 'w').close()
        r = self.post('/api/meshinfo', {'files': ['/etc/passwd', self.outside, inside]})
        self.assertEqual(r.status, 200)
        self.assertEqual(self.ran, [['--mesh-info', inside]])

    def test_reveal_is_refused_when_served(self):
        r = self.post('/api/reveal', {'path': '/etc/passwd'})
        self.assertEqual(r.status, 403)
        self.assertEqual(self.revealed, [])


if __name__ == '__main__':
    unittest.main()
