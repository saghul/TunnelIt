# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#

from application.configuration import ConfigSection, ConfigSetting

from tunnelit import configuration_filename
from tunnelit.datatypes import IPAddress, NonNegativeInteger, Port, PortRange


class ServerConfig(ConfigSection):
    __cfgfile__ = configuration_filename
    __section__ = 'TunnelIt'

    listen_ip = ConfigSetting(type=IPAddress, value=None)
    listen_port = ConfigSetting(type=Port, value=2222)
    port_range = ConfigSetting(type=PortRange, value=PortRange('10000:20000'))
    public_key = 'keys/public.key'
    private_key = 'keys/private.key'
    session_timeout = ConfigSetting(type=NonNegativeInteger, value=30)

