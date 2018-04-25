# -*- coding: utf-8 -*-

####################################################################################
# Integron_Finder - Integron Finder aims at detecting integrons in DNA sequences   #
# by finding particular features of the integron:                                  #
#   - the attC sites                                                               #
#   - the integrase                                                                #
#   - and when possible attI site and promoters.                                   #
#                                                                                  #
# Authors: Jean Cury, Bertrand Neron, Eduardo PC Rocha                             #
# Copyright © 2015 - 2018  Institut Pasteur, Paris.                                #
# See the COPYRIGHT file for details                                               #
#                                                                                  #
# integron_finder is free software: you can redistribute it and/or modify          #
# it under the terms of the GNU General Public License as published by             #
# the Free Software Foundation, either version 3 of the License, or                #
# (at your option) any later version.                                              #
#                                                                                  #
# integron_finder is distributed in the hope that it will be useful,               #
# but WITHOUT ANY WARRANTY; without even the implied warranty of                   #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                    #
# GNU General Public License for more details.                                     #
#                                                                                  #
# You should have received a copy of the GNU General Public License                #
# along with this program (COPYING file).                                          #
# If not, see <http://www.gnu.org/licenses/>.                                      #
####################################################################################

import os
import tempfile
import shutil
import argparse
import re
import distutils.spawn

try:
    from tests import IntegronTest
except ImportError as err:
    msg = "Cannot import integron_finder: {0!s}".format(err)
    raise ImportError(msg)

from integron_finder.utils import FastaIterator
from integron_finder.topology import Topology
from integron_finder.config import Config
from integron_finder import integrase

_call_ori = integrase.call


class TestFindIntegrase(IntegronTest):

    def setUp(self):
        if 'INTEGRON_HOME' in os.environ:
            self.integron_home = os.environ['INTEGRON_HOME']
            self.local_install = True
        else:
            self.local_install = False
            self.integron_home = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'tmp_test_integron_finder')
        if os.path.exists(self.tmp_dir) and os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        os.makedirs(self.tmp_dir)

        self.args = argparse.Namespace()
        self.args.attc_model = 'attc_4.cm'
        self.args.cpu = 1
        self.args.hmmsearch = distutils.spawn.find_executable('hmmsearch')
        self.args.prodigal = distutils.spawn.find_executable("prodigal")
        integrase.call = self.mute_call(_call_ori)

    def tearDown(self):
        integrase.call = _call_ori
        try:
            shutil.rmtree(self.tmp_dir)
            pass
        except:
            pass


    def test_find_integrase_gembase(self):
        cfg = Config(self.args)
        self.args.gembase = True
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))

        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        prot_file = os.path.join(self.tmp_dir, replicon_name + ".prt")

        shutil.copyfile(self.find_data(os.path.join('Proteins', replicon.id + ".prt")), prot_file)

        integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)

        for suffix in ('_intI.res', '_intI_table.res', '_phage_int.res', '_phage_int_table.res'):
            res = os.path.join(self.tmp_dir, replicon.id + suffix)
            self.assertTrue(os.path.exists(res))


    def test_find_integrase_no_gembase_with_protfile(self):
        cfg = Config(self.args)
        self.args.gembase = False
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 200

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")
        shutil.copyfile(self.find_data(os.path.join('Proteins', replicon.id + ".prt")), prot_file)

        integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        for suffix in ('_intI.res', '_intI_table.res', '_phage_int.res', '_phage_int_table.res'):
            res = os.path.join(self.tmp_dir, replicon.id + suffix)
            self.assertTrue(os.path.exists(res))
        replicon.__class__.__len__ = len_ori


    def test_find_integrase_no_gembase_with_protfile_empty(self):
        cfg = Config(self.args)
        self.args.gembase = False
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 200

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")
        open(prot_file, 'w').close()
        with self.assertRaises(RuntimeError) as ctx:
            with self.catch_log():
                integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        self.assertTrue(re.match("^The protein file: '.*' is empty cannot perform hmmsearch on it.$",
                                 str(ctx.exception)))
        replicon.__class__.__len__ = len_ori


    def test_find_integrase_no_gembase_no_protfile_short_seq(self):
        cfg = Config(self.args)
        self.args.gembase = False
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 200

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")

        integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        for suffix in ('_intI.res', '_intI_table.res', '_phage_int.res', '_phage_int_table.res'):
            res = os.path.join(self.tmp_dir, replicon.id + suffix)
            self.assertTrue(os.path.exists(res))
        replicon.__class__.__len__ = len_ori


    def test_find_integrase_no_gembase_no_protfile_long_seq(self):
        cfg = Config(self.args)
        self.args.gembase = False
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 500000

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")

        shutil.copyfile(self.find_data(os.path.join('Proteins', replicon.id + ".prt")), prot_file)

        integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        for suffix in ('_intI.res', '_intI_table.res', '_phage_int.res', '_phage_int_table.res'):
            res = os.path.join(self.tmp_dir, replicon.id + suffix)
            self.assertTrue(os.path.exists(res))
        replicon.__class__.__len__ = len_ori


    def test_find_integrase_no_gembase_no_protfile_no_prodigal(self):
        self.args.hmmsearch = 'foo'
        self.args.gembase = False
        cfg = Config(self.args)
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 500000

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")

        shutil.copyfile(self.find_data(os.path.join('Proteins', replicon.id + ".prt")), prot_file)

        with self.assertRaises(RuntimeError) as ctx:
            integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        self.assertTrue(re.search("failed : \[Errno 2\] No such file or directory: 'foo'", str(ctx.exception)))

        replicon.__class__.__len__ = len_ori


    def test_find_integrase_no_gembase_no_protfile(self):
        cfg = Config(self.args)
        self.args.gembase = False
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = self.find_data(os.path.join('Replicons', replicon_name + '.fst'))
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        len_ori = replicon.__class__.__len__
        replicon.__class__.__len__ = lambda x: 500000
        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")

        with self.assertRaises(RuntimeError) as ctx:
            integrase.find_integrase('foo', replicon,  prot_file, self.tmp_dir, cfg)
        self.assertTrue(str(ctx.exception).endswith('failed returncode = 5'.format(cfg.prodigal)))

        replicon.__class__.__len__ = len_ori


    def test_find_integrase_gembase_no_hmmer_no_replicon(self):
        self.args.gembase = True
        self.args.hmmsearch = 'foo'
        cfg = Config(self.args)
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = os.path.join(self._data_dir, 'Replicons', replicon_name + '.fst')
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")

        with self.assertRaises(RuntimeError) as ctx:
            integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        self.assertTrue(re.match("^foo .* failed : \[Errno 2\] No such file or directory: 'foo'",
                                 str(ctx.exception)))


    def test_find_integrase_gembase_hmmer_error(self):
        self.args.gembase = True
        self.args.cpu = 'foo'
        cfg = Config(self.args)
        cfg._prefix_data = os.path.join(os.path.dirname(__file__), 'data')

        replicon_name = 'acba.007.p01.13'
        replicon_path = os.path.join(self._data_dir, 'Replicons', replicon_name + '.fst')
        topologies = Topology('lin')
        with FastaIterator(replicon_path) as sequences_db:
            sequences_db.topologies = topologies
            replicon = next(sequences_db)

        prot_file = os.path.join(self.tmp_dir, replicon.id + ".prt")
        shutil.copyfile(os.path.join(self._data_dir, 'Proteins', replicon.id + ".prt"),
                        prot_file)
        with self.assertRaises(RuntimeError) as ctx:
            integrase.find_integrase(replicon_path, replicon, prot_file, self.tmp_dir, cfg)
        self.assertTrue(str(ctx.exception).endswith('failed return code = 1'))
