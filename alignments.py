#! /usr/bin/python


import os
import sys
import argparse
import multiprocessing
from Bio import Entrez
from Bio import SeqIO
from Bio.Align.Applications import MuscleCommandline

from util import Color



def assemble_fasta_clusters(gb, clusters):
    """
    Inputs the dictionary of all GenBank sequences and a list of clustered accessions.
    Only make fasta files of clusters containing 4 taxa or more.
    Outputs a list of FASTA files, each file containing an unaligned sequence cluster,
    and an updated list of clustered accessions.
    """
    cluster_files = []
    if not os.path.exists("clusters"):
        os.makedirs("clusters")
    i = 0
    to_delete = []
    for cluster in clusters:
        # get all OTUs in cluster
        otus = []
        for seq_key in cluster:
            descriptors = gb[seq_key].description.split(" ")
            otu = descriptors[0] + " " + descriptors[1]
            if otu not in otus:
                otus.append(otu)
        # make fasta file if > 3 OTUs in cluster
        otus_in_cluster = []
        if len(otus) > 3:
            sequences = []
            for seq_key in cluster:
                descriptors = gb[seq_key].description.split(" ")
                otu = descriptors[0] + " " + descriptors[1]
                # do not allow duplicate OTUs in cluster
                if otu not in otus_in_cluster:
                    sequences.append(gb[seq_key])
                    otus_in_cluster.append(otu)
            file_name = "clusters/" + str(i) + ".fasta"
            file = open(file_name, "wb")
            SeqIO.write(sequences, file, 'fasta')
            file.close()
            cluster_files.append(file_name)
            i += 1
        else:
            to_delete.append(cluster)
    for cluster in to_delete:
        del clusters[clusters.index(cluster)]
    return cluster_files, clusters



def align_clusters(cluster_files):
    """
    Inputs a list of FASTA files, each file containing an unaligned sequence cluster.
    Creates new processes to align each sequence cluster.
    Returns a list of aligned FASTA files.
    """
    # TODO:
    # blast to check forward/reverse sequences...
    alignment_files = []
    if not os.path.exists("alignments"):
        os.makedirs("alignments")
    color = Color()
    print(color.blue + "Spawning " + color.red + str(multiprocessing.cpu_count()) + color.blue + " processes to align clusters." + color.done)
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    alignment_files = pool.map(align_cluster, cluster_files)
    pool.close()
    pool.join()
    return alignment_files



def align_cluster(cluster_file):
    """
    Worker fuction for align_clusters
    Inputs a FASTA file containing an unaligned sequence cluster.
    Uses MUSCLE to align the cluster.
    """
    alignment_file = "alignments" + cluster_file[cluster_file.index("/"):]
    muscle_cline = MuscleCommandline(input=cluster_file, out=alignment_file)
    color = Color()
    print(color.red + str(muscle_cline) + color.done)
    sys.stdout.flush()
    stdout, stderr = muscle_cline()
    return alignment_file



def print_region_data(alignment_files):
    """
    Inputs a list of FASTA files, each containing an aligned sequence cluster
    Prints the name of each DNA region, the number of taxa, the aligned length,
    missing data (%), and taxon coverage density
    TODO: calculate the variable characters (and %), PI characters (and %)
    """
    # TODO: calculate the variable characters (and %), PI characters (and %)
    # first get list of all taxa
    taxa = []
    for alignment in alignment_files:
        records = SeqIO.parse(alignment, "fasta")
        for record in records:
            descriptors = record.description.split(" ")
            taxon = descriptors[1] + " " + descriptors[2]
            if taxon not in taxa:
                taxa.append(taxon)

    # print data for each region
    i = 0
    color = Color()
    for alignment in alignment_files:
        records = list(SeqIO.parse(alignment, "fasta"))
        descriptors = records[0].description.split(" ")
        print(color.blue + "Aligned cluster #: " + color.red + str(i) + color.done)
        print(color.yellow + "DNA region: " + color.red + " ".join(descriptors[3:]) + color.done)
        print(color.yellow + "Taxa: " + color.red + str(len(records)) + color.done)
        print(color.yellow + "Aligned length: " + color.red + str(len(records[0].seq)) + color.done)
        print(color.yellow + "Missing data (%): " + color.red + str(round(100 - (100 * len(records)/float(len(taxa))), 1)) + color.done)
        print(color.yellow + "Taxon coverage density: "  + color.red + str(round(len(records)/float(len(taxa)), 2)) + color.done)
        i += 1



def concatenate(alignment_files):
    """
    Inputs a list of FASTA files, each containing an aligned sequence cluster
    Returns a concatenated FASTA file
    """
    # first build up a dictionary of all OTUs
    otus = {}
    for alignment in alignment_files:
        records = SeqIO.parse(alignment, "fasta")
        for record in records:
            # sample record.description:
            # AF495760.1 Lythrum salicaria chloroplast ribulose 1,5-bisphosphate carboxylase/oxygenase large subunit-like mRNA, partial sequence
            descriptors = record.description.split(" ")
            otu = descriptors[1] + " " + descriptors[2]
            if otu not in otus:
                otus[otu] = ""

    # now concatenate the sequences
    total_length = 0
    for alignment in alignment_files: 
        records = SeqIO.parse(alignment, "fasta")
        # make sure to only add 1 sequence per cluster for each otu
        already_added = []
        for record in records:
            descriptors = record.description.split(" ")
            otu = descriptors[1] + " " + descriptors[2]
            if otu not in already_added:
                otus[otu] = otus[otu] + record.seq
                already_added.append(otu)
            loci_length = len(record.seq)
        total_length += loci_length
        # add gaps for any OTU that didn't have a sequence
        for otu in otus:
            if len(otus[otu]) < total_length:
                otus[otu] = otus[otu] + make_gaps(loci_length)

    # write to FASTA file
    f = open("alignments/final.fasta", "w")
    for otu in otus:
        # >otu
        # otus[otu]
        f.write("> " + otu + "\n")
        sequence = str(otus[otu])
        i = 0
        while i < len(sequence):
            f.write(sequence[i:i+80] + "\n")
            i += 80
    f.close()
    return "alignments/final.fasta"



def make_gaps(length):
    """
    Inputs an integer.
    Returns a string of '-' of length
    """
    gap = ""
    for i in range(length):
        gap = "-" + gap
    return gap



def calculate_supermatrix_attributes():
    """
    Prints out details on the final aligned super matrix.
    TODO: make the output of this more useful
    """
    records = SeqIO.parse("alignments/final.fasta", "fasta")
    num_records = 0
    total_gap = 0
    for record in records:
        otu = record.description
        gap = 0
        for letter in record.seq:
            if letter == '-':
                gap += 1
                total_gap += 1
        print("Taxa: " + otu + " % gaps = " + str(round(gap/float(len(record.seq)), 2)))
        num_records += 1
        matrix_length = len(record.seq)
    print("Total number of taxa = " + str(num_records))
    print("Total length of matrix = " + str(matrix_length))
    print("Total % gaps = " + str(round(total_gap/float(matrix_length * num_records), 2)))

