# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#
__all__ = ['Database']

from twisted.enterprise import adbapi
from urlparse import urlparse


db_modules = {
                'mysql':    'MySQLdb',
                'sqlite':   'sqlite3'
             }

def parse_db_uri(uri):
    scheme, netloc, path, params, query, fragment = urlparse(uri)
    if scheme not in db_modules:
        raise ValueError('Invalid DB scheme')
    if scheme == 'sqlite' and netloc == ':memory:':
        raise ValueError('SQLite in-memory DB is not supported')
    if netloc:
        user_pass, sep, host = netloc.partition('@')
        user, sep, password = user_pass.partition(':')
    else:
        user = password = host = ''
    if scheme == 'sqlite' and netloc and not path:
        db = netloc
    elif not path:
        raise ValueError('DB not specified')
    else:
        db = path.strip('/') if scheme != 'sqlite' else path
    module = db_modules[scheme.lower()]
    return module, user, password, host, db


class Database(object):

    def __init__(self, dburi):
        try:
            module, user, password, host, db = parse_db_uri(dburi)
        except ValueError, e:
            raise RuntimeError('Error parsing DB URI: %s' % e)
        else:
            if module == 'MySQLdb':
                self.conn = adbapi.ConnectionPool(module, user=user, passwd=password, host=host, db=db)
            elif module == 'sqlite3':
                self.conn = adbapi.ConnectionPool(module, database=db, check_same_thread=False)

    def get_userid(self, username):
        return self.conn.runQuery("SELECT id FROM users WHERE name = ? LIMIT 1", [username])

    def get_user_keys(self, userid):
        return self.conn.runQuery("SELECT key FROM keys WHERE user_id = ?", [userid])


