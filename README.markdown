# TunnelIt!

## What is TunnelIt?

TunnelIt is a *Proof of Concept* SSH reverse forward server. It was inspired by the popular service [Tunnlr](http://tunnlr.com)
It allows users to allocate ports on the server which will forward traffic tunneled over SSH to a port of their choice in their machines. This is
particularly useful when doing web development, since users don't need to open ports in their routers. Authentication is performed by using SSH
public keys.

## Installation

Dependencies:
- twisted
- python-application
- sqlobject

Dependencies can be installed with easy_install, pip, or whatever tool of your choice.

## Configuration

The bundled `tunnelit.ini.sample` contains detailed explanations about what settings can be toggled.

## Running

By default TunnelIt will fork and got to the background, but if you would like to prevent it from forking you may run it as follows:

    tunnelit-server --no-fork

## Connecting to TunnelIt

Assuming that the server runs on example.com, a user which wants a random remote port to be forwarded to his local port 3000 would do the
following:

ssh -n -N -g -R :0:0.0.0.0:3000 username@example.com

## Under the hoods

If you run more than one TunnelIt servers and do DNS based load balancing, there is no way for the user to know tho which of the TunnelIt server
he connected. TunnelIt will send information about the connection as SSH debug messages. They can be seen by using the `-v` modifier when running
the ssh command:

    debug1: Remote: >>> TunnelIt Remote Host: tun01.example.com/1.2.3.4
    debug1: Remote: >>> TunnelIt Remote Port: 34036

This means that the user would need to go to http://tun01.example.com:34036 or he could use the IP address (1.2.3.4) instead of the domain name.

## ToDo

See the TODO file

## Contributing

Patches are always welcome! :-)

## License

GPL v3

## Author

Saúl Ibarra Corretgé, aka saghul || saghul (at) gmail (dot) com

