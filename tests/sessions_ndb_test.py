# -*- coding: utf-8 -*-
from google.appengine.api import datastore_errors
from google.appengine.api import memcache

import webapp2
from webapp2_extras import sessions
from webapp2_extras import sessions_ndb

import test_base


class App(object):
    @property
    def config(self):
        config = sessions.default_config.copy()
        config['secret_key'] = 'my-super-secret'
        return {'webapp2_extras.sessions': config}

app = App()


class TestNdbSession(test_base.BaseTestCase):
    factory = sessions_ndb.DatastoreSessionFactory

    def test_get_save_session(self):

        # Round 1 -------------------------------------------------------------

        req = webapp2.Request.blank('/')
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)

        rsp = webapp2.Response()
        # Nothing changed, we want to test anyway.
        store.save_sessions(rsp)

        session['a'] = 'b'
        session['c'] = 'd'
        session['e'] = 'f'

        store.save_sessions(rsp)

        # Round 2 -------------------------------------------------------------

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)
        self.assertEqual(session['a'], 'b')
        self.assertEqual(session['c'], 'd')
        self.assertEqual(session['e'], 'f')

        session['g'] = 'h'

        rsp = webapp2.Response()
        store.save_sessions(rsp)

        # Round 3 -------------------------------------------------------------

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)
        self.assertEqual(session['a'], 'b')
        self.assertEqual(session['c'], 'd')
        self.assertEqual(session['e'], 'f')
        self.assertEqual(session['g'], 'h')

        # Round 4 -------------------------------------------------------------

        # For this attempt we don't want the memcache backup.
        sid = session.container.sid
        memcache.delete(sid)

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)
        self.assertEqual(session['a'], 'b')
        self.assertEqual(session['c'], 'd')
        self.assertEqual(session['e'], 'f')
        self.assertEqual(session['g'], 'h')

    def test_flashes(self):

        # Round 1 -------------------------------------------------------------

        req = webapp2.Request.blank('/')
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)
        flashes = session.get_flashes()
        self.assertEqual(flashes, [])
        session.add_flash('foo')

        rsp = webapp2.Response()
        store.save_sessions(rsp)

        # Round 2 -------------------------------------------------------------

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)

        flashes = session.get_flashes()
        self.assertEqual(flashes, [(u'foo', None)])

        flashes = session.get_flashes()
        self.assertEqual(flashes, [])

        session.add_flash('bar')
        session.add_flash('baz', 'important')

        rsp = webapp2.Response()
        store.save_sessions(rsp)

        # Round 3 -------------------------------------------------------------

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)

        flashes = session.get_flashes()
        self.assertEqual(flashes, [(u'bar', None), (u'baz', 'important')])

        flashes = session.get_flashes()
        self.assertEqual(flashes, [])

        rsp = webapp2.Response()
        store.save_sessions(rsp)

        # Round 4 -------------------------------------------------------------

        cookies = rsp.headers.get('Set-Cookie')
        req = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        req.app = app
        store = sessions.SessionStore(req)

        session = store.get_session(factory=self.factory)
        flashes = session.get_flashes()
        self.assertEqual(flashes, [])

    def test_misc(self):
        p = sessions_ndb._PickledProperty(dict)
        self.assertRaises(datastore_errors.BadValueError, p._validate, ['foo'])

        s = sessions_ndb.Session(id='foo')
        key = s.put()

        s = key.get()
        self.assertEqual(s.data, None)


if __name__ == '__main__':
    test_base.main()
