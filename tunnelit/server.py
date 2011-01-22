# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#

__all__ = ['TunnelItServer']

import os
import socket
import struct

from application import log
from application.python.util import Singleton
from Crypto.PublicKey import RSA
from zope.interface import implements

for name in ['epollreactor', 'kqreactor', 'pollreactor']:
    try:
        __import__('twisted.internet.%s' % name, globals(), locals(), fromlist=[name]).install()
    except ImportError:
        continue
    else:
        break

from twisted.cred import portal, checkers
from twisted.cred.credentials import ISSHPrivateKey
from twisted.conch.avatar import ConchUser
from twisted.conch.error import ConchError, ValidPublicKey
from twisted.conch.ssh import factory, keys, forwarding, transport, userauth
from twisted.conch.ssh.connection import SSHConnection as _SSHConnection, MSG_CHANNEL_CLOSE
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.python import failure, randbytes

log.msg("Twisted is using %s" % reactor.__module__.rsplit('.', 1)[-1])

from tunnelit.configuration import ServerConfig
from tunnelit.database import Database
from tunnelit.util import makedirs


class SSHConnection(_SSHConnection):
    def sendClose(self, channel):
        if channel.localClosed:                                                                                                                                                              
            return # we're already closed                                                                                                                                                    
        log.msg('sending close %i' % channel.id)
        try:
            self.transport.sendPacket(MSG_CHANNEL_CLOSE, struct.pack('>L', self.channelsToRemoteChannel[channel]))
        except KeyError:
            # If there is nothing listening on the remote port neither
            # ssh_CHANNEL_OPEN() nor ssh_CHANNEL_OPEN_CONFIRMATION() method of
            # twisted.conch.ssh.connection.SSHConnection is called, so
            # self.channelsToRemoteChannel dict is empty when sendClose() is called
            pass
        channel.localClosed = True
        if channel.localClosed and channel.remoteClosed:
            self.channelClosed(channel)


class SSHFactory(factory.SSHFactory):
    services = {
                'ssh-userauth': userauth.SSHUserAuthServer,
                'ssh-connection': SSHConnection
               }


class Listener(object):
    def __init__(self, listener, timer):
        self.listener = listener
        self.disconnect_timer = timer


class SSHAvatar(ConchUser):
    def __init__(self, username):
        ConchUser.__init__(self)
        self.username = username
        self.listeners = {}

    def _terminate_session(self):
        self.conn.transport.sendDisconnect(transport.DISCONNECT_BY_APPLICATION, 'session timed out')

    def global_tcpip_forward(self, data):
        hostToBind, portToBind = forwarding.unpackGlobal_tcpip_forward(data)
        try:
            listener = reactor.listenTCP(portToBind, 
                                         forwarding.SSHListenForwardingFactory(self.conn,
                                                                               (hostToBind, portToBind),
                                                                               forwarding.SSHListenServerForwardingChannel))
            # We don't set the 'interface' attribute because we want to listen on 0.0.0.0
            # Same effect as adding GatewayPorts yes to sshd_config
        except CannotListenError:
            return 0
        else:
            timer = reactor.callLater(ServerConfig.session_timeout, self._terminate_session)
            self.listeners[(hostToBind, portToBind)] = Listener(listener, timer)
            if portToBind == 0:
                portToBind = listener.getHost().port
                return 1, struct.pack('>L', portToBind)
            else:
                return 1
        finally:
            hostname = TunnelItServer().hostname
            self.conn.transport.sendDebug(">>> TunnelIt Remote Host: %s/%s" % (hostname[0], hostname[2][0]), alwaysDisplay=True)
            self.conn.transport.sendDebug(">>> TunnelIt Remote Port: %s" % portToBind, alwaysDisplay=True)

    def global_cancel_tcpip_forward(self, data):
        hostToBind, portToBind = forwarding.unpackGlobal_tcpip_forward(data)
        listener = self.listeners.get((hostToBind, portToBind), None)
        if not listener:
            return 0
        del self.listeners[(hostToBind, portToBind)]
        listener.disconnect_timer.cancel()
        listener.listener.stopListening()
        return 1

    def logout(self):
        # remove all listeners
        for listener in self.listeners.itervalues():
            if listener.disconnect_timer.active():
                listener.disconnect_timer.cancel()
            listener.listener.stopListening()
        log.msg('avatar %s logging out (%i)' % (self.username, len(self.listeners)))


class DBPublicKeyChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (ISSHPrivateKey, )

    def __init__(self, db):
        self.db = db

    def requestAvatarId(self, credentials):
        # credentials is an instance of twisted.cred.credentials.SSHPrivateKey
        d = self.db.get_userid(credentials.username)
        d.addCallback(self._got_userid_result, credentials)
        d.addErrback(self._got_userid_error, credentials)
        return d

    def _got_userid_result(self, rows, credentials):
        if not rows:
            return failure.Failure(ConchError("User not found"))
        user_id = rows[0][0]
        d = self.db.get_user_keys(user_id)
        d.addCallback(self._got_keys_result, credentials)
        d.addErrback(self._got_keys_error, credentials)
        return d

    def _got_userid_error(self, error, credentials):
        if not error.check(ValidPublicKey):
            return failure.Failure(ConchError('Error authenticating %s: %s' % (credentials.username, error.getErrorMessage())))
        else:
            raise ValidPublicKey()

    def _got_keys_result(self, rows, credentials):
        if not rows:
            return failure.Failure(ConchError("No keys found"))
        user_keys = []
        for key in rows[0]:
            try:
                user_keys.append(keys.Key.fromString(data=key).blob())
            except keys.BadKeyError:
                pass
        if credentials.blob not in user_keys:
            return failure.Failure(ConchError("Key not recognized"))
        if not credentials.signature:
            return failure.Failure(ValidPublicKey())
        try:
            public_key = keys.Key.fromString(data=credentials.blob)
        except (keys.BadKeyError, keys.EncryptedKeyError):
            return failure.Failure(ConchError("Public key error"))
        if public_key.verify(credentials.signature, credentials.sigData):
            return credentials.username
        else:
            return failure.Failure(ConchError("Incorrect signature"))

    def _got_keys_error(self, error, credentials):
        if not error.check(ValidPublicKey):
            return failure.Failure(ConchError(error.getErrorMessage()))
        else:
            raise ValidPublicKey()


class SSHRealm(object):
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        avatar = SSHAvatar(avatarId)
        return interfaces[0], avatar, avatar.logout


class TunnelItServer(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.db = Database('sqlite://test.sqlite')
        self.ssh_factory = SSHFactory()
        self.ssh_factory.portal = portal.Portal(SSHRealm())
        self.ssh_factory.portal.registerChecker(DBPublicKeyChecker(self.db))
        public_key_str, private_key_str = self._get_rsa_keys()
        self.ssh_factory.publicKeys = {'ssh-rsa': keys.Key.fromString(data=public_key_str)}
        self.ssh_factory.privateKeys = {'ssh-rsa': keys.Key.fromString(data=private_key_str)}
        try:
            self.hostname = socket.gethostbyaddr(socket.gethostname())
        except socket.error, e:
            raise RuntimeError("Error getting hostname: %s" % e)

    def _get_rsa_keys(self):
        public_key = os.path.realpath(ServerConfig.public_key)
        private_key = os.path.realpath(ServerConfig.private_key)
        config_directory = os.path.dirname(public_key)
        if config_directory:
            makedirs(config_directory)
        config_directory = os.path.dirname(private_key)
        if config_directory:
            makedirs(config_directory)
        if not os.path.isfile(public_key) and not os.path.isfile(private_key):
            log.msg("Generating RSA keypair...")
            rsa_key = RSA.generate(1024, randbytes.secureRandom)
            public_key_str = keys.Key(rsa_key).public().toString('openssh')
            private_key_str = keys.Key(rsa_key).toString('openssh')
            file(public_key, 'w+b').write(public_key_str)
            file(private_key, 'w+b').write(private_key_str)
            log.msg("Done")
        else:
            try:
                public_key_str = file(public_key).read()
                private_key_str = file(private_key).read()
            except IOError, e:
                raise RuntimeError('Error getting public/private keys: %s' % e)
        return public_key_str, private_key_str

    def _log_listen_info(self):
        log.msg('TunnelIt server listening on %s:%d' % (ServerConfig.listen_ip or '0.0.0.0', ServerConfig.listen_port))

    def start(self):
        reactor.callLater(0, self._log_listen_info)
        reactor.listenTCP(ServerConfig.listen_port, self.ssh_factory, interface=ServerConfig.listen_ip or '')
        reactor.run(installSignalHandlers=False)

    def stop(self):
        log.msg('Stopping...')
        reactor.stop()


