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
from subprocess import call

from Bio import BiopythonExperimentalWarning
import warnings
warnings.simplefilter('ignore', FutureWarning)
warnings.simplefilter('ignore', BiopythonExperimentalWarning)

import numpy as np
import pandas as pd
from Bio import SeqFeature
from Bio import SeqIO

from .utils import get_name_from_path, read_multi_prot_fasta
from .hmm import read_hmm


def func_annot(integrons, replicon, prot_file, hmm_files, cfg, out_dir='.', evalue=10, coverage=0.5):
    """
    | Call hmmmer to annotate CDS associated with the integron.
    | Use Resfams per default (Gibson et al, ISME J.,  2014)

    :param integrons: integrons list to annotate
    :type integrons: list of :class:`integron_finder.integron.Integron` objects.
    :param replicon: replicon where the integrons were found (genomic fasta file)
    :type replicon: :class:Bio.Seq.SeqRecord` object
    :param str prot_file: the path to a fasta file containing the sequence proteins of the replicon
                          these proteins constitute the bank scanned by hmmsearch
    :param str hmm_files: list of path of hmm profiles to use to scan the prot_file
    :param cfg: the configuration for this analyse
    :type cfg: :class:`integron_finder.config.Config`
    :param str out_dir: the path of the directory where to store the results
    :param float evalue:
    :param float coverage:
    :return: None.
             | But several files per hmm file are produced.

             * subseqprot.tmp: fasta file containing a subset of protfile (the proteins belonging to the integron)
             * <hmm>_fa.res: an output of the hmm search.
             * <hmm>_fa_table.res: an output of the hmm search in tabulated format.

    """

    print "# Start Functional annotation... : "
    prot_tmp = os.path.join(out_dir, replicon.name + "_subseqprot.tmp")

    for integron in integrons:
        if os.path.isfile(prot_tmp):
            os.remove(prot_tmp)

        if integron.type() != "In0" and not integron.proteins.empty:

            func_annotate_res = pd.DataFrame(columns=["Accession_number",
                                                      "query_name", "ID_query",
                                                      "ID_prot", "strand",
                                                      "pos_beg", "pos_end", "evalue"])

            prot_to_annotate = []
            # It's protein file, fasta_reader is dedicated fr dna
            all_prots = read_multi_prot_fasta(prot_file)

            for prot_nb, prot in enumerate(all_prots, 1):
                if prot.id in integron.proteins.index:
                    prot_to_annotate.append(prot)

            SeqIO.write(prot_to_annotate, prot_tmp, "fasta")
            for hmm in hmm_files:
                name_wo_ext = "{}_{}".format(replicon.name, get_name_from_path(hmm))
                hmm_out = os.path.join(out_dir, "{}_fa.res".format(name_wo_ext))
                hmm_tableout = os.path.join(out_dir, "{}_fa_table.res".format(name_wo_ext))
                hmm_cmd = [cfg.hmmsearch,
                            "-Z", str(prot_nb),
                            "--cpu", str(cfg.cpu),
                            "--tblout", hmm_tableout,
                            "-o", hmm_out,
                            hmm,
                            prot_tmp]

                try:
                    returncode = call(hmm_cmd)
                except Exception as err:
                    raise RuntimeError("{0} failed : {1}".format(hmm_cmd[0], err))
                if returncode != 0:
                    raise RuntimeError("{0} failed return code = {1}".format(hmm_cmd[0], returncode))
                hmm_in = read_hmm(replicon.name, hmm_out, cfg, evalue=evalue, coverage=coverage
                                  ).sort_values("evalue").drop_duplicates(subset="ID_prot")
                func_annotate_res = pd.concat([func_annotate_res, hmm_in])
            func_annotate_res = func_annotate_res.sort_values("evalue").drop_duplicates(subset="ID_prot")

            integron.proteins.loc[func_annotate_res.ID_prot, "evalue"] = func_annotate_res.evalue.values
            integron.proteins.loc[func_annotate_res.ID_prot, "annotation"] = func_annotate_res.query_name.values
            integron.proteins.loc[func_annotate_res.ID_prot, "model"] = func_annotate_res.ID_query.values
            integron.proteins = integron.proteins.astype(dtype=integron.dtype)


def add_feature(replicon, integron_desc, prot_file, dist_threshold):
    """
    Add integron annotation to the replicon.

    :param replicon: The Replicon to annotate
    :type replicon: a :class:`Bio.Seq.SeqRecord` object.
    :param integron_desc:
    :type integron_desc: a :class:`pandas.DataFrame`
    :param str prot_file: the path to the fasta file containing the translation of the replicon.
    :param int dist_threshold: Two elements are aggregated if they are distant of dist_threshold or less.
    """
    integron_desc = integron_desc.set_index("ID_integron").copy()
    for integron_id in integron_desc.index.unique():
        if isinstance(integron_desc.loc[integron_id], pd.Series):
            # There is only one element in this integron
            the_elt = integron_desc.loc[integron_id]
            type_integron = the_elt.type
            start_integron = the_elt.pos_beg
            end_integron = the_elt.pos_end
            tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(start_integron - 1, end_integron),
                                        strand=0,
                                        type="integron",
                                        qualifiers={"integron_id": integron_id, "integron_type": type_integron}
                                        )
            replicon.features.append(tmp)
            if the_elt.type_elt == "protein":

                tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(start_integron - 1, end_integron),
                                            strand=the_elt.strand,
                                            type="CDS" if the_elt.annotation != "intI" else "integrase",
                                            qualifiers={"protein_id": the_elt.element,
                                                        "gene": the_elt.annotation,
                                                        "model": the_elt.model}
                                            )

                tmp.qualifiers["translation"] = [prt for prt in read_multi_prot_fasta(prot_file)
                                                 if prt.id == the_elt.element][0].seq
                replicon.features.append(tmp)

            else:
                tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(start_integron - 1, end_integron),
                                            strand=the_elt.strand,
                                            type=the_elt.type_elt,
                                            qualifiers={the_elt.type_elt: the_elt.element, "model": the_elt.model}
                                            )

                replicon.features.append(tmp)

        else:
            # there are several elements in this integron (promoter, attc, protein, ...)
            # so desc is a dataframe each row representing one elt
            integron = integron_desc.loc[integron_id]
            type_integron = integron.type.values[0]
            # Should only be true if integron over edge of replicon:

            diff = integron.pos_beg.diff() > dist_threshold

            if diff.any():
                pos = np.where(diff)[0][0]
                start_integron_1 = integron.pos_beg.values[pos]
                end_integron_1 = len(replicon)
                start_integron_2 = 1
                end_integron_2 = integron.pos_end.values[pos-1]

                f1 = SeqFeature.FeatureLocation(start_integron_1 - 1, end_integron_1)
                f2 = SeqFeature.FeatureLocation(start_integron_2 - 1, end_integron_2)
                tmp = SeqFeature.SeqFeature(location=f1 + f2,
                                            strand=0,
                                            type="integron",
                                            qualifiers={"integron_id": integron_id, "integron_type": type_integron}
                                            )
            else:
                start_integron = integron.pos_beg.values[0]
                end_integron = integron.pos_end.values[-1]

                tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(start_integron - 1, end_integron),
                                            strand=0,
                                            type="integron",
                                            qualifiers={"integron_id": integron_id, "integron_type": type_integron}
                                            )
            replicon.features.append(tmp)
            for idx, elt in integron.iterrows():
                if elt.type_elt == "protein":
                    tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(elt.pos_beg - 1, elt.pos_end),
                                                strand=elt.strand,
                                                type="CDS" if elt.annotation != "intI" else "integrase",
                                                qualifiers={"protein_id": elt.element,
                                                            "gene": elt.annotation,
                                                            "model": elt.model}
                                                )

                    tmp.qualifiers["translation"] = [prt for prt in read_multi_prot_fasta(prot_file)
                                                     if prt.id == elt.element][0].seq
                    replicon.features.append(tmp)
                else:
                    tmp = SeqFeature.SeqFeature(location=SeqFeature.FeatureLocation(elt.pos_beg - 1, elt.pos_end),
                                                strand=elt.strand,
                                                type=elt.type_elt,
                                                qualifiers={elt.type_elt: elt.element, "model": elt.model}
                                                )

                    replicon.features.append(tmp)

    # We get a ValueError otherwise, eg:
    # ValueError: Locus identifier 'gi|00000000|gb|XX123456.2|' is too long
    if len(replicon.name) > 16:
        replicon.name = replicon.name[-16:]
