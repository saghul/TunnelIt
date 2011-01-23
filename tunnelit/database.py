# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#
__all__ = ['Database', 'DatabaseError']

from application import log
from application.python.util import Null, Singleton
from sqlobject import connectionForURI, sqlhub, IntCol, SQLObject, StringCol
from twisted.internet.threads import deferToThread


def defer_to_thread(func):
    """Decorator to run DB queries in Twisted's thread pool"""
    def wrapper(*args, **kw):
        return deferToThread(func, *args, **kw)
    return wrapper


class Users(SQLObject):
    username = StringCol()


class UserKeys(SQLObject):
    user_id = IntCol()
    key = StringCol(sqlType='LONGTEXT')


class DatabaseError(Exception): pass

class Database(object):
    __metaclass__ = Singleton

    def __init__(self, dburi):
        if ':memory:' in dburi:
            log.warn('SQLite in-memory DB is not supported')
            dburi = None
        self._uri = dburi
        if self._uri is not None:
            try:
                self.conn = connectionForURI(self._uri)
                sqlhub.processConnection = self.conn
            except Exception, e:
                log.error('Error connection with the DB: %s' % e)
                self.conn = Null
        else:
            self.conn = Null

    def _create_table(self, klass):
        if klass._connection is Null or klass.tableExists():
            return
        else:
            log.warn('Table %s does not exists. Creating it now.' % klass.sqlmeta.table)
            saved = klass._connection.debug
            try:
                klass._connection.debug = True
                klass.createTable()
            finally:
                klass._connection.debug = saved

    @defer_to_thread
    def initialize(self):
        if self.conn is not Null:
            for klass in Users, UserKeys:
                self._create_table(klass)

    @defer_to_thread
    def get_user_keys(self, username):
        try:
            user = Users.selectBy(username=username)[0]
        except IndexError:
            raise DatabaseError("User %s doesn't exist" % username)
        else:
            user_keys = UserKeys.selectBy(user_id=user.id)
            if user_keys.count() == 0:
                raise DatabaseError("No keys found for user %s" % username)
            return [key.key for key in user_keys]


