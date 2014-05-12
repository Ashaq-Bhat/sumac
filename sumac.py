#! /usr/bin/python
"""

SUMAC: supermatrix constructor
sumac.py

Will Freyman
freyman@berkeley.edu

Freyman, W.A. 2014. Supermatrix Constructor (SUMAC): a Python module for data mining GenBank and building phylogenetic supermatrices.

Python module that:
1: Downloads GenBank database of the specified GB division (PLN, MAM, etc)
2: Perform exhaustive all-by-all BLAST comparisons of each ingroup and outgroup sequence.
3: Alternatively (much faster) uses a FASTA file of guide sequences to define each cluster. 
   Each ingroup/outgroup sequence is BLASTed against the guide sequences.
4: Build clusters of sequences:
	- use single-linkage hierarchical clustering algorithm
	- distance threshold default BLASTn e-value 1.0e-10 
        - uses sequence length percent similarity cutoff default 0.5
	- discards clusters that are not phylogenetically informative (< 4 taxa)
5: Aligns each cluster of sequences using MUSCLE.
6: Concatenates the clusters creating a supermatrix.

Optimized to run on multicore servers with the use of parallel multiple processes.

Requirements:
    Python 2.7
    Biopython
    MUSCLE
    BLAST+

usage: sumac.py [-h] [--download_gb DOWNLOAD_GB] [--ingroup INGROUP]
                      [--outgroup OUTGROUP] [--max_outgroup MAX_OUTGROUP]
                      [--evalue EVALUE] [--length LENGTH] [--guide GUIDE]

optional arguments:
  -h, --help            show this help message and exit
  --download_gb DOWNLOAD_GB, -d DOWNLOAD_GB
                        Name of the GenBank division to download (e.g. PLN or
                        MAM).
  --ingroup INGROUP, -i INGROUP
                        Ingroup clade to build supermatrix.
  --outgroup OUTGROUP, -o OUTGROUP
                        Outgroup clade to build supermatrix.
  --max_outgroup MAX_OUTGROUP, -m MAX_OUTGROUP
                        Maximum number of taxa to include in outgroup.
                        Defaults to 10.
  --evalue EVALUE, -e EVALUE
                        BLAST E-value threshold to cluster taxa. Defaults to
                        0.1
  --length LENGTH, -l LENGTH
                        Threshold of sequence length percent similarity to 
			cluster taxa. Defaults to 0.5
  --guide GUIDE, -g GUIDE
                        FASTA file containing sequences to guide cluster 
			construction. If this option is selected then 
			all-by-all BLAST comparisons are not performed.


Example: 
sumac.py -d pln -i Onagraceae -o Lythraceae

If you already downloaded the GB database:
sumac.py -i Onagraceae -o Lythraceae

Using guide sequences to cluster:
sumac.py -i Onagraceae -o Lythraceae -g guides.fasta

"""

import os
import sys
import argparse
import multiprocessing
from Bio import Entrez
from Bio import SeqIO
from Bio.Blast.Applications import NcbiblastnCommandline
from Bio.Align.Applications import MuscleCommandline
from Bio.Blast import NCBIXML

from util import Color
from util import GenBank



class SeqKeys:
    """
    Class responsible for managing keys to all sequences in ingroup and outgroup.
    """

    ingroup_keys = []
    outgroup_keys = []

    def write_keys_to_file():

    def read_keys_from_file():

def get_in_out_groups(gb, ingroup, outgroup):
    """
    Takes as input a dictionary of SeqRecords gb and the names of ingroup and outgroup clades.
    Returns lists of keys to SeqRecords for the ingroup and outgroup.
    """
    keys = gb.keys()
    ingroup_keys = []
    outgroup_keys = []
    total = len(keys)
    i = 0
    for key in keys:
	if ingroup in gb[key].annotations['taxonomy']:
            ingroup_keys.append(key)
	elif outgroup in gb[key].annotations['taxonomy']:
	    outgroup_keys.append(key)
	sys.stdout.write('\r' + Color.yellow + 'Ingroup sequences found: ' + Color.red + str(len(ingroup_keys)) + Color.yellow \
	    + '  Outgroup sequences found: ' + Color.red + str(len(outgroup_keys)) + Color.yellow + '  Percent searched: ' \
	    + Color.red + str(round( 100 * float(i) / total , 1)) + Color.done)    
	sys.stdout.flush() 
	i += 1
	## FOR TESTING ONLY
	#if len(ingroup_keys) == 50:  ##
        #    sys.stdout.write("\n")   ## FOR TESTING ONLY
        #    sys.stdout.flush()       ## # FOR TESTING ONLY
	#    return ingroup_keys, outgroup_keys    # FOR TESTING ONLY
	## FOR TESTING ONLY
	## remove above
    sys.stdout.write("\n")
    sys.stdout.flush()
    return ingroup_keys, outgroup_keys



class DistanceMatrix:
    """
    Builds distance matrix
    """

def distance_matrix_worker(seq_keys, length_threshold, dist_matrix, already_compared, lock, process_num):
    """
    Worker process for make_distance_matrix(). Takes a list "already_compared" of sequences that have
    already had all pairwise comparisons. Each worker process will work making pairwise comparisons
    for a different sequence, adding them to the "already_compared" list as they are completed.
    """
    # each process must load its own sqlite gb
    gb_dir = os.path.abspath("genbank/")
    gb = SeqIO.index_db(gb_dir + "/gb.idx")
    process_num = str(process_num)
    i = 0
    for key in seq_keys:
        # check whether another process is already comparing this row
	compare_row = False
	with lock:
            if key not in already_compared:
	        already_compared.append(key)
		compare_row = True
	if compare_row:
	    # get the sequence record to compare
	    record1 = gb[key]
	    output_handle = open('subject' + process_num + '.fasta', 'w')
            SeqIO.write(record1, output_handle, 'fasta')
            output_handle.close()
            j = 0
            for key2 in seq_keys:
	        # only calculate e-values for pairs that have not yet been compared
	        if dist_matrix[i][j] == 99:
	            if key == key2:
		        row = dist_matrix[i]
			row[j] = 0.0
			dist_matrix[i] = row
		    # check sequence lengths
		    else:
			# print("proc # = "+process_num+" i = "+str(i)+ " j = "+str(j))
			record2 = gb[key2]
		        length1 = len(record1.seq)
		        length2 = len(record2.seq)
			# set distance to 50.0 if length similarity threshold not met
		        if (length1 > length2 * (1 + float(length_threshold))) or (length1 < length2 * (1 - float(length_threshold))):
			    row = dist_matrix[i]
			    row[j] = 50.0
			    dist_matrix[i] = row
			    row = dist_matrix[j]
			    row[i] = 50.0
			    dist_matrix[j] = row
		        else:
		            # do the blast comparison
                            output_handle = open('query' + process_num + '.fasta', 'w')
                            SeqIO.write(record2, output_handle, 'fasta')
                            output_handle.close()

                            blastn_cmd = NcbiblastnCommandline(query='query' + process_num + '.fasta', subject='subject' + process_num + \
			        '.fasta', out='blast' + process_num + '.xml', outfmt=5)
                            stdout, stderr = blastn_cmd()
                            blastn_xml = open('blast' + process_num + '.xml', 'r')
                            blast_records = NCBIXML.parse(blastn_xml)

                            for blast_record in blast_records:
			        if blast_record.alignments:
			            if blast_record.alignments[0].hsps:
                                        # blast hit found, set distance to e-value
			                row = dist_matrix[i]
					row[j] = blast_record.alignments[0].hsps[0].expect
					dist_matrix[i] = row
					row = dist_matrix[j]
					row[i] = blast_record.alignments[0].hsps[0].expect
					dist_matrix[j] = row
		                else:
			            # no blast hit found, set distance to default 10.0
		                    row = dist_matrix[i]
				    row[j] = 10.0
				    dist_matrix[i] = row
				    row = dist_matrix[j]
				    row[i] = 10.0
				    dist_matrix[j] = row
		            blastn_xml.close()
	        j += 1
	i += 1
	# update status
	percent = str(round(100 * len(already_compared)/float(len(seq_keys)), 2))
	sys.stdout.write('\r' + Color.blue + 'Completed: ' + Color.red + str(len(already_compared)) + '/' + str(len(seq_keys)) + ' (' + percent + '%)' + Color.done)    
	sys.stdout.flush()    
    # done looping through all keys, now clean up
    os.remove("blast" + process_num + ".xml")
    os.remove("query" + process_num + ".fasta")
    os.remove("subject" + process_num + ".fasta")



def make_distance_matrix(gb, seq_keys, length_threshold):
    """
    Takes as input a dictionary of SeqRecords gb and the keys to all sequences.
    length_threshold is the threshold of sequence length percent similarity to cluster taxa.
    For example if length_threshold = 0.25, and one sequence has
    length 100, the other sequence must have length 75 to 125. If the lengths are not similar
    enough the distance is set to 50 (which keeps them from being clustered).
    Returns a 2 dimensional list of distances. Distances are blastn e-values.
    """
    lock = multiprocessing.Lock()
    manager = multiprocessing.Manager()
    already_compared = manager.list()
    dist_matrix = manager.list()
    row = []
    for i in range(len(seq_keys)):
        row.append(99)
    for i in range(len(seq_keys)):
	dist_matrix.append(row)

    num_cores = multiprocessing.cpu_count()
    print(Color.blue + "Spawning " + Color.red + str(num_cores) + Color.blue + " processes to make distance matrix." + Color.done)
    processes = []
    
    for i in range(num_cores):
        p = multiprocessing.Process(target=distance_matrix_worker, args=(seq_keys, length_threshold, dist_matrix, already_compared, lock, i))
	p.start()
	processes.append(p)

    for p in processes:
        p.join()
    
    sys.stdout.write("\n")
    sys.stdout.flush()
    return dist_matrix



def make_clusters(seq_keys, distance_matrix, threshold=(1.0/10**10)):
    """
    Input: seq_keys a list of all sequences used in the analysis, distance_matrix based on BLAST e-values, and an optional e-value threshold for clustering.
    Output: a list of clusters (each cluster is itself a list of keys to sequences)
    This function is a wrapper around the recursive function merge_closest_clusters.
    """
    # put each sequence in its own cluster
    clusters = []
    for seq in seq_keys:
        clusters.append([seq])
    return merge_closest_clusters(clusters, distance_matrix, threshold)



def merge_closest_clusters(clusters, distance_matrix, threshold):
    """
    Input: a list of clusters, distance_matrix based on BLAST e-values, and the e-value threshold to stop clustering
    Output: a list of clusters (each cluster is itself a list of keys to sequences)
    Single-linkage hierarchical clustering algorithm.
    """
    cluster1 = 0
    cluster2 = 0
    min_distance = 99
    x = 0
    y = 0
    # find the most similar pair of clusters (or the first pair with distance = 0)
    while x < len(distance_matrix):
        y = x + 1
        while y < len(distance_matrix):
	    if x != y:
		if distance_matrix[x][y] < min_distance:
		    min_distance = distance_matrix[x][y]
		    cluster1 = x
		    cluster2 = y
		if min_distance == 0:
		    break
            y += 1
	if min_distance == 0:
     	    break
	x += 1
	
    # check to see if we are done
    if min_distance > threshold:
        return clusters
    
    # merge the two clusters
    for sequence in clusters[cluster2]:
        clusters[cluster1].append(sequence)
    del clusters[cluster2]

    # update distance matrix
    for i in range(len(distance_matrix[cluster1])):
        if distance_matrix[cluster1][i] > distance_matrix[cluster2][i]:
	    row = distance_matrix[cluster1]
	    row[i] = distance_matrix[cluster2][i]
	    distance_matrix[cluster1] = row
	    row = distance_matrix[i]
	    row[cluster1] = distance_matrix[cluster2][i]
	    distance_matrix[i] = row
    del distance_matrix[cluster2]
    for i in range(len(distance_matrix)):
        row = distance_matrix[i]
	del row[cluster2]
	distance_matrix[i] = row

    return merge_closest_clusters(clusters, distance_matrix, threshold)



def make_guided_clusters(guide_seq, all_seq_keys, length_threshold, evalue_threshold):
    """
    Input: name of FASTA file containing guide sequences, dictionary of all GenBank sequences,
    a list of ingroup/outgroup sequences, the e-value threshold to cluster, and the
    threshold of sequence length percent similarity to cluster taxa.
    Returns a list of clusters (each cluster is itself a list of keys to sequences).
    """
    lock = multiprocessing.Lock()
    manager = multiprocessing.Manager()
    already_compared = manager.list()
    clusters = manager.list()

    # check for fasta file of guide sequences
    if not os.path.isfile(guide_seq):
	print(Color.red + "FASTA file of guide sequences not found. Please re-try." + Color.done)
	sys.exit(0)
    else:
        # initialize an empty list for each cluster
        guide_sequences = SeqIO.parse(open(guide_seq, "rU"), "fasta")
	for guide in guide_sequences:
            clusters.append([])

    num_cores = multiprocessing.cpu_count()
    print(Color.blue + "Spawning " + Color.red + str(num_cores) + Color.blue + " processes to make clusters." + Color.done)
    processes = []
    
    for i in range(num_cores):
        p = multiprocessing.Process(target=make_guided_clusters_worker, args=(guide_seq, all_seq_keys, \
	    length_threshold, evalue_threshold, clusters, already_compared, lock, i))
	p.start()
	processes.append(p)

    for p in processes:
        p.join()
    
    sys.stdout.write("\n")
    sys.stdout.flush()
    return clusters



def make_guided_clusters_worker(guide_seq, all_seq_keys, length_threshold, evalue_threshold, clusters, already_compared, lock, process_num):
    """
    Worker process for make_guided_clusters(). Each process will compare all the ingroup/outgroup sequences
    to a guide sequence, adding that guide sequence to the already_compared list.
    """
    # each process must load its own sqlite gb
    gb_dir = os.path.abspath("genbank/")
    gb = SeqIO.index_db(gb_dir + "/gb.idx")
    process_num = str(process_num)

    # open guide fasta file
    if os.path.isfile(guide_seq):
        guide_sequences = list(SeqIO.parse(open(guide_seq, "rU"), "fasta"))
    else:        
	print(Color.red + "FASTA file of guide sequences not found. Please re-try." + Color.done)
	sys.exit(0)

    # remember how many guide sequences there are
    num_guides = len(list(guide_sequences))

    for guide in guide_sequences:
        # check whether another process is already comparing this guide sequence
	compare_guide = False
	with lock:
            if guide.id not in already_compared:
	        already_compared.append(guide.id)
		compare_guide = True
	if compare_guide:
            # loop through each ingroup/outgroup sequence and blast to guide seq
	    output_handle = open('subject' + process_num + '.fasta', 'w')
            SeqIO.write(guide, output_handle, 'fasta')
            output_handle.close()
            for key in all_seq_keys:
	        record = gb[key]
		length1 = len(guide.seq)
		length2 = len(record.seq)
		# check if length similarity threshold met
		if (length1 < length2 * (1 + float(length_threshold))) and (length1 > length2 * (1 - float(length_threshold))):
		    # do the blast comparison
                    output_handle = open('query' + process_num + '.fasta', 'w')
                    SeqIO.write(record, output_handle, 'fasta')
                    output_handle.close()

                    blastn_cmd = NcbiblastnCommandline(query='query' + process_num + '.fasta', subject='subject' + process_num + \
			'.fasta', out='blast' + process_num + '.xml', outfmt=5)
                    stdout, stderr = blastn_cmd()
                    blastn_xml = open('blast' + process_num + '.xml', 'r')
                    blast_records = NCBIXML.parse(blastn_xml)

                    for blast_record in blast_records:
		        if blast_record.alignments:
			    if blast_record.alignments[0].hsps:
                                # blast hit found, add sequence to cluster
			        with lock:
				    temp_cluster = clusters[guide_sequences.index(guide)]
				    temp_cluster.append(key)
				    clusters[guide_sequences.index(guide)] = temp_cluster
		    blastn_xml.close()
	# update status
	percent = str(round(100 * len(already_compared)/float(num_guides), 2))
	sys.stdout.write('\r' + Color.blue + 'Completed: ' + Color.red + str(len(already_compared)) + '/' + str(num_guides) + ' (' + percent + '%)' + Color.done)    
	sys.stdout.flush()    
    # done looping through all guides, now clean up
    if os.path.isfile("blast" + process_num + ".xml"):
        os.remove("blast" + process_num + ".xml")
    if os.path.isfile("query" + process_num + ".fasta"):
        os.remove("query" + process_num + ".fasta")
    if os.path.isfile("subject" + process_num + ".fasta"):
        os.remove("subject" + process_num + ".fasta")



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
    print(Color.blue + "Spawning " + Color.red + str(multiprocessing.cpu_count()) + Color.blue + " processes to align clusters." + Color.done)
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
    print(Color.red + str(muscle_cline) + Color.done)
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
    for alignment in alignment_files:
        records = list(SeqIO.parse(alignment, "fasta"))
	descriptors = records[0].description.split(" ")
	print(Color.blue + "Aligned cluster #: " + Color.red + str(i) + Color.done)
	print(Color.yellow + "DNA region: " + Color.red + " ".join(descriptors[3:]) + Color.done)
	print(Color.yellow + "Taxa: " + Color.red + str(len(records)) + Color.done)
	print(Color.yellow + "Aligned length: " + Color.red + str(len(records[0].seq)) + Color.done)
	print(Color.yellow + "Missing data (%): " + Color.red + str(round(100 - (100 * len(records)/float(len(taxa))), 1)) + Color.done)
	print(Color.yellow + "Taxon coverage density: "  + Color.red + str(round(len(records)/float(len(taxa)), 2)) + Color.done)
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



def main():
    # parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--download_gb", "-d", help="Name of the GenBank division to download (e.g. PLN or MAM).")
    parser.add_argument("--ingroup", "-i", help="Ingroup clade to build supermatrix.")
    parser.add_argument("--outgroup", "-o", help="Outgroup clade to build supermatrix.")
    parser.add_argument("--max_outgroup", "-m", help="Maximum number of taxa to include in outgroup. Defaults to 10.")
    parser.add_argument("--evalue", "-e", help="BLAST E-value threshold to cluster taxa. Defaults to 0.1")
    parser.add_argument("--length", "-l", help="Threshold of sequence length percent similarity to cluster taxa. Defaults to 0.5")
    parser.add_argument("--guide", "-g", help="""FASTA file containing sequences to guide cluster construction. If this option is 
                                                 selected then all-by-all BLAST comparisons are not performed.""")
    args = parser.parse_args()
   
    print("")
    print(Color.blue + "SUMAC: supermatrix constructor" + Color.done)
    print("")

    # download and set up sqllite db
    if args.download_gb:
        gb_division = str(args.download_gb).lower()
        GenBank.download_gb_db(gb_division)
        print(Color.yellow + "Setting up SQLite database..." + Color.done)
        gb = GenBank.setup_sqlite()
    elif not os.path.exists("genbank/gb.idx"):
        print(Color.red + "GenBank database not downloaded. Re-run with the -d option. See --help for more details." + Color.done)
        sys.exit(0)
    else:
        print(Color.purple + "Genbank database already downloaded. Indexing sequences..." + Color.done)
	gb_dir = os.path.abspath("genbank/")
	gb = SeqIO.index_db(gb_dir + "/gb.idx")
    print(Color.purple + "%i sequences indexed!" % len(gb) + Color.done)

    # check for ingroup and outgroup
    if args.ingroup and args.outgroup:
        ingroup = args.ingroup
        outgroup = args.outgroup
    else:
        print(Color.red + "Please specify ingroup and outgroup. See --help for details." + Color.done)
	sys.exit(0)
	
    # search db for sequences
    print(Color.blue + "Outgroup = " + outgroup)
    print("Ingroup = " + ingroup + Color.done)
    print(Color.blue + "Searching for ingroup and outgroup sequences..." + Color.done)
    ingroup_keys, outgroup_keys = get_in_out_groups(gb, ingroup, outgroup)        
    all_seq_keys = ingroup_keys + outgroup_keys

    # determine sequence length similarity threshold
    length_threshold = 0.5
    if args.length:
	length_threshold = args.length
    print(Color.blue + "Using sequence length similarity threshold " + Color.red + str(length_threshold) + Color.done)

    # determine e-value threshold
    evalue_threshold = (1.0/10**10)
    if args.evalue:
        evalue_threshold = float(args.evalue)
    print(Color.blue + "Using BLAST e-value threshold " + Color.red + str(evalue_threshold) + Color.done)

    # now build clusters, first checking whether we are using FASTA file of guide sequences
    # or doing all-by-all comparisons
    if args.guide:
        # use FASTA file of guide sequences
        print(Color.blue + "Building clusters using the guide sequences..." + Color.done)
	clusters = make_guided_clusters(args.guide, all_seq_keys, length_threshold, evalue_threshold)
    else:
        # make distance matrix
        print(Color.blue + "Making distance matrix for all sequences..." + Color.done)
        distance_matrix = make_distance_matrix(gb, all_seq_keys, length_threshold)

        # cluster sequences
        print(Color.purple + "Clustering sequences..." + Color.done)
	clusters = make_clusters(all_seq_keys, distance_matrix, evalue_threshold)
    
    print(Color.purple + "Found " + Color.red + str(len(clusters)) + Color.purple + " clusters." + Color.done)
    if len(clusters) == 0:
        print(Color.red + "No clusters found." + Color.done)
        sys.exit(0)

    # filter clusters, make FASTA files
    print(Color.yellow + "Building sequence matrices for each cluster." + Color.done)
    cluster_files, clusters = assemble_fasta_clusters(gb, clusters)
    print(Color.purple + "Kept " + Color.red + str(len(clusters)) + Color.purple + " clusters, discarded those with < 4 taxa." + Color.done)
    if len(clusters) == 0:
        print(Color.red + "No clusters left to align." + Color.done)
	sys.exit(0)

    # now align each cluster with MUSCLE
    print(Color.blue + "Aligning clusters with MUSCLE..." + Color.done)
    alignment_files = align_clusters(cluster_files)
    print_region_data(alignment_files)

    # concatenate alignments
    print(Color.purple + "Concatenating alignments..." + Color.done)
    final_alignment = concatenate(alignment_files)
    print(Color.yellow + "Final alignment: " + Color.red + "alignments/final.fasta" + Color.done)

    # TODO:
    # reduce the number of outgroup taxa, make graphs, etc



if __name__ == "__main__":
    main()
