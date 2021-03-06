#
# Copyright (c) 2013, Centre for Microscopy and Microanalysis
#   (University of Queensland, Australia)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the University of Queensland nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS AND CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


import logging
from re import compile
from os import path

from tardis.tardis_portal.models import Schema, DatafileParameterSet,\
    ParameterName, DatafileParameter, Dataset_File
from tardis.tardis_portal.ParameterSetManager import ParameterSetManager
from tardis.tardis_portal.models.parameters import DatasetParameter
from . import DataGrabberFilter

logger = logging.getLogger(__name__)

def source_path(datafile, exclude=[], strip='S:\\', 
                windowsPath=True, rootdir=''):
    for ps in datafile.getParameterSets():
        if ps.schema.namespace != DataGrabberFilter.SCHEMA2:
            continue
        psm = ParameterSetManager(ps)
        try:
            pathname = psm.get_param('instrument_pathname', value=True)
            if pathname.startswith(strip):
                pathname = pathname[len(strip):]
            if windowsPath:
                pathname = pathname.replace('\\', '/')
            for pattern in exclude:
                regex = compile(pattern)
                if regex.match(pathname):
                    return None
            return pathname
        except DatafileParameter.DoesNotExist:
            pass
    return None
