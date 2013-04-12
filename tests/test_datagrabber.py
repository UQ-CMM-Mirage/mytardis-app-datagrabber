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

from os import path
from compare import expect, ensure

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from tardis.apps.datagrabber import DataGrabberFilter
from tardis.tardis_portal.models import User, UserProfile, \
    ExperimentACL, Experiment, Dataset, Dataset_File, Replica, Location
from tardis.tardis_portal.models.parameters import DatasetParameterSet
from tardis.tardis_portal.ParameterSetManager import ParameterSetManager

from tardis.tardis_portal.tests.test_download import get_size_and_sha512sum


class DataGrabberFilterTestCase(TestCase):

    def setUp(self):
        # Create test owner without enough details
        username, email, password = ('testuser',
                                     'testuser@example.test',
                                     'password')
        user = User.objects.create_user(username, email, password)
        profile = UserProfile(user=user, isDjangoAccount=True)
        profile.save()

        Location.force_initialize()

        # Create test experiment and make user the owner of it
        experiment = Experiment(title='Text Experiment',
                                institution_name='Test Uni',
                                created_by=user)
        experiment.save()
        acl = ExperimentACL(
            pluginId='django_user',
            entityId=str(user.id),
            experiment=experiment,
            canRead=True,
            isOwner=True,
            aclOwnershipType=ExperimentACL.OWNER_OWNED,
            )
        acl.save()

        dataset = Dataset(description='dataset description...')
        dataset.save()
        dataset.experiments.add(experiment)
        dataset.save()

        def create_datafile(filename):
            testfile = path.join(path.dirname(__file__), 'fixtures',
                                 filename)

            size, sha512sum = get_size_and_sha512sum(testfile)

            datafile = Dataset_File(dataset=dataset,
                                    filename=path.basename(testfile),
                                    size=size,
                                    sha512sum=sha512sum)
            datafile.save()
            base_url = 'file://' + path.abspath(path.dirname(testfile))
            location = Location.load_location({
                'name': 'test-grabber', 'url': base_url, 'type': 'external',
                'priority': 10, 'transfer_provider': 'local'})
            replica = Replica(datafile=datafile,
                              url='file://'+path.abspath(testfile),
                              protocol='file',
                              location=location)
            replica.verify()
            replica.save()
            return Dataset_File.objects.get(pk=datafile.pk)

        self.dataset = dataset
        self.datafiles = [create_datafile('data_grabber_test1.admin'),
                          create_datafile('testfile.txt')
                         ] 


    def testFilter(self):
        DataGrabberFilter()(None, instance=self.datafiles[0])

        # Check a DATASET parameter set was created
        dataset = Dataset.objects.get(id=self.dataset.id)
        expect(dataset.getParameterSets().count()).to_equal(1)

        # Check all the expected parameters are there
        psm = ParameterSetManager(dataset.getParameterSets()[0])
        expect(psm.get_param('admin-filename', True))\
            .to_equal(self.datafiles[0].filename)
        expect(psm.get_param('user_name', True)).to_equal('s.crawley')
        expect(psm.get_param('facility_name', True)).to_equal('QBP NIKON TIE')
        expect(psm.get_param('account_name', True)).to_equal('200 - CMM STAFF')
        expect(psm.get_param('session_uuid', True)).to_equal(
            'cbc86da5-e143-4a11-9951-abaffef70efa')
        expect(psm.get_param('record_uuid', True)).to_equal(
            'ddf0df63-d985-4ffa-9102-e34a78b3fd1f')
        
        # Repeat for the datafile parameters
        expect(self.datafiles[0].getParameterSets().count()).to_equal(0)
        expect(self.datafiles[1].getParameterSets().count()).to_equal(1)
        psm = ParameterSetManager(self.datafiles[1].getParameterSets()[0])
        expect(psm.get_param('instrument_pathname', True)).to_equal(
            'S:\\Garry\\testfile.txt')

        # Check we won't create a duplicate dataset
        DataGrabberFilter()(None, instance=self.datafiles[0])
        dataset = Dataset.objects.get(id=self.dataset.id)
        expect(dataset.getParameterSets().count()).to_equal(1)

