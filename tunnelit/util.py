# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#

# Some code borrowed from SIPSIMPLE SDK project (http://sipsimpleclient.com)

import errno
import os

def makedirs(path):                                                                                                                                                       
    try:                                                                                                                                                                  
        os.makedirs(path)                                                                                                                                                 
    except OSError, e:                                                                                                                                                    
        if e.errno == errno.EEXIST and os.path.isdir(path): # directory exists                                                                                            
            return                                                                                                                                                        
        raise                                                                                                                                                             
            
