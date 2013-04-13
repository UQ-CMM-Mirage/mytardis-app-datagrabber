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
from os import path
from urllib2 import urlopen
from json import load

from tardis.tardis_portal.models import Schema, DatafileParameterSet,\
    ParameterName, DatasetParameter, Dataset_File
from tardis.tardis_portal.ParameterSetManager import ParameterSetManager
from tardis.tardis_portal.models.parameters import DatasetParameter

logger = logging.getLogger(__name__)

class DataGrabberFilter(object):
    """This filter collects source metadata for a dataset and its datafiles
    from a data grabber '.admin' file.

    :param name: the short name of the schema.
    :type name: string
    :param schema: the name of the schema to load data into.
    :type schema: string
    """

    SCHEMA = 'http://cmm.uq.edu.au/#dataset-source-schema'
    SCHEMA2 = 'http://cmm.uq.edu.au/#datafile-source-schema'
    DATASET_ATTRS = {
        'userName': 'user_name',
        'facilityName': 'facility_name',
        'accountName': 'account_name',
        'recordUuid': 'record_uuid',
        'sessionUuid': 'session_uuid'
    }
    DATAFILE_ATTRS = {
        'facilityFilePathname': 'instrument_pathname'
    }

    def __init__(self):
        pass


    def __call__(self, sender, **kwargs):
        """post save callback entry point.

        :param sender: The model class.
        :param instance: The actual instance being saved.
        :param created: A boolean; True if a new record was created.
        :type created: bool
        """
        datafile = kwargs.get('instance')
        try:
            logger.debug('Checking if file is admin metadata')
            if self.is_admin_file(datafile): 
                # Don't check further if it's already processed
                if self.is_already_processed(datafile):
                    logger.debug('Admin metadata file was already processed.')
                    return
                # Get file contents (remotely if required)
                contents = self.load_file_contents(datafile)
                if self.is_grabber_metadata(contents):
                    schemas = self._get_schemas()
                    logger.debug('Processing admin metadata file')
                    metadata = self.get_metadata(contents)
                    self.save_dataset_metadata(
                        datafile, schemas[0], metadata[0]) 
                    self.save_datafile_metadata(
                        datafile, schemas[1], metadata[1]) 
        except Exception as e:
            print "Failed - %s\n" % e
            logger.debug(e)
            return

    def is_grabber_metadata(self, content):
        try:
            return content['facilityId']
        except KeyError:
            return False

    @class_method
    def _get_schemas(cls):
        """Return the schema object that the paramaterset will use.
        """
        try:
            return (Schema.objects.get(namespace__exact=self.SCHEMA), 
                    Schema.objects.get(namespace__exact=self.SCHEMA2)) 
        except Schema.DoesNotExist:
            from django.core.management import call_command
            call_command('loaddata', 'source_metadata_schemas')
            return self._get_schemas()

    def is_already_processed(self, datafile):
        def get_filename(ps):
            try:
                return ParameterSetManager(ps)\
                    .get_param('admin-filename', True)
            except DatasetParameter.DoesNotExist:
                return None

        def processed_files(dataset):
            return [get_filename(ps)
                    for ps in datafile.dataset.getParameterSets()]

        return datafile.filename in processed_files(datafile.dataset)

    def is_admin_file(self, datafile):
        mimetype = datafile.get_mimetype()
        return ((mimetype == 'text/plain' or 
                 mimetype == 'application/json') and
                datafile.filename.endswith('.admin'))

    def load_file_contents(self, datafile):
        from contextlib import closing
        file_ = datafile.get_file()
        if file_ == None:
            return None
        with closing(file_) as f:
            return load(f)
            
    def get_metadata(self, json):
        df_metadata = {}
        ds_metadata = {}
        for (key, value) in json.items():
            if self.DATASET_ATTRS.has_key(key):
                ds_metadata[self.DATASET_ATTRS[key]] = value
            if key == 'datafiles':
                for datafile in value:
                    filepath = datafile['sourceFilePathname']
                    filename = path.basename(filepath)
                    for (key2, value2) in datafile.items():
                        if self.DATAFILE_ATTRS.has_key(key2):
                            m = df_metadata.setdefault(filename, {})
                            m[self.DATAFILE_ATTRS[key2]] = value2

        return (ds_metadata, df_metadata)

    def save_dataset_metadata(self, datafile, schema, metadata):
        psm = ParameterSetManager(parentObject=datafile.dataset,
                                  schema=schema.namespace)
        psm.set_param('admin-filename', datafile.filename)
        self._save_metadata(psm, schema, metadata)

    def save_datafile_metadata(self, datafile, schema, metadata):
        for (filename, file_metadata) in metadata.items():
            try:
                file_datafile = Dataset_File.objects.get(
                    dataset=datafile.dataset, filename=filename)
                psm = ParameterSetManager(
                    parentObject=file_datafile, schema=schema.namespace)
                self._save_metadata(psm, schema, file_metadata)
            except Dataset_File.DoesNotExist as e:
                logger.debug(e)
                pass
    
    def _save_metadata(self, psm, schema, metadata):
        for (key, value) in metadata.items():
            try:
                psm.set_param(key, value)
            except ValueError:
                pn = ParameterName.objects.get(name=key, schema=schema)
                psm.set_param(key, value.strip(pn.units))

