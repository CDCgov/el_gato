#!/usr/bin/env python3
import argparse
import logging
import os
import re
import subprocess
import sys
import multiprocessing
import time
import shutil

t0 = time.time()


class Ref:
    file = "Ref_Paris_mompS_2.fasta"
    name = "Paris_mompS_R"
    source = "Contig = gi|54295983|ref|NC_006368.1| location on contig = 3453389_3455389"
    seq = "GTTATCAATAAAATGGAAACTCAATAATAAACAAGTGGAGACAAGGCATGTTTAGTTTGAAAAAAACAGCAGTGGCAGTACTCGCCTTAGGAAGCGGTGCAGTGTTTGCTGGAACCATGGGACCAGTTTGCACCCCAGGTAATGTAACTGTTCCTTGCGAAAGAACTGCATGGGATATTGGTATCACCGCACTATATTTGCAACCAATCTATGATGCTGATTGGGGCTACAATGGTTTCACCCAAGTTGGTGGCTGGCAGCATTGGCATGATGTTGACCATGAGTGGGATTGGGGCTTCAAATTAGAAGGTTCTTATCACTTCAATACTGGTAATGACATCAATGTGAACTGGTATCATTTTGATAATGACAGTGATCACTGGGCTGATTTTGCTAACTGGCACAACTACAACAACAAGTGGGATGCTGTTAATGCTGAATTAGGTCAATTCGTAGATTTCAGCGCTAACAAGAAAATGCGTTTCCACGGCGGTGTTCAATACGCTCGCATTGAAGCTGATGTGAACCGTTATTTCAATAACTTTGCCTTTAACGGGTTCAACTCTAAGTTCAATGGCTTTGGTCCTCGCACTGGTTTAGACATGAACTATGTATTTGGCAATGGCTTTGGTGTTTATGCTAAAGGCGCTGCTGCTATTCTGGTTGGTACCAGCGATTTCTACGATGGAATCAACTTCATTACTGGTTCTAAAAATGCTATCGTTCCTGAGTTGGAAGCTAAGCTTGGTGCTGATTACACTTACGCAATGGCTCAAGGCGATTTGACTTTAGACGTTGGTTACATGTGGTTTAACTACTTCAACGCTATGCACAATACTGGCGTATTTAATGGATTTGAAACTGATTTCGCAGCTTCTGGTCCTTACATTGGCTTGAAGTATGTTGGTAATGTGTAATTTGTTAAGTTGATAAGAAATTTCAGCAATACTGTTGACTTTATAGAAGTCCGGCTGGATAATTTATCCA"
    allele_start = 367
    allele_stop = 718
    flank_start = 15
    flank_stop = 972
    analysis_path = ""
    locus_order = ["flaA", "pilE", "asd", "mip", "mompS", "proA", "neuA_neuAH"]
    ispcr_opt = "stdout -out=fa -minPerfect=5 -tileSize=6 -maxSize=1200 -stepSize=5"
    mompS_primer1 = "TTGACCATGAGTGGGATTGG\tTGGATAAATTATCCAGCCGGACTTC"
    mompS_primer2 = "TTGACCATGAGTGGGATTGG\tCAGAAGCTGCGAAATCAG"
    prereq_programs = ["bwa", "sambamba", "freebayes", "samtools", "makeblastdb", "blastn", "isPcr"]


""" Get commandline arguments """
parser = argparse.ArgumentParser(description="""Legionella in silico SBT script. 
Needs either reads file and/or genome assembly.

Notes on arguments:
(1) If only reads are provided, de novo assembly is performed and SBT is called using assembly/mapping/alignment route 
(2) If only an assembly is provided, a BLAST and in silico PCR based approach is adopted. 
(3) If both are provided, SBT is called using a combination of assembly and mapping.
""", formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
group1 = parser.add_argument_group(title='Input files',
                                   description="Please specify either reads file and/or a genome assembly file")
group1.add_argument("-r1", help="Read(s) file", type=str, required=False, metavar="Read 1 file")
group1.add_argument("-r2", help="Read 2 file", type=str, required=False, metavar="Read 2 file")
group1.add_argument("-a", help="Assembly file for isolate", type=str, required=False)
group2 = parser.add_argument_group(title='Optional arguments')
group2.add_argument("-h", "--help", action="help", help="Show this help message and exit")
group2.add_argument("-t", help="Number of threads to run the programs (default: %(default)s)", type=int, required=False,
                    default=4)
group2.add_argument("-d", help="Variant read depth cutoff (default: %(default)s)", type=int, required=False, default=3)
group2.add_argument("--prefix", help="Prefix for output files (default: %(default)s)", type=str, required=False,
                    default="run")
group2.add_argument("-out", "-o", help="Output folder name (default: %(default)s)", type=str, required=False,
                    default="out")
group2.add_argument("-log", help="Logging file prefix (default: %(default)s)", type=str, required=False, default="run")
group2.add_argument("-overwrite", "-w", help="Overwrite output directory (default: %(default)s)", action="store_true",
                    required=False, default=False)
group2.add_argument("-sbt", "-s", help="Database containing SBT allele files (default: %(default)s)", type=str,
                    required=False, default="./")
group2.add_argument("-suffix", "-x", help="Suffix of SBT allele files (default: %(default)s)", type=str,
                    required=False,
                    default="_alleles.tfa")
group2.add_argument("-profile", help="Allele profile to ST file (default: %(default)s)", type=str, required=False,
                    default="lpneumophila.txt")
group2.add_argument("-verbose", "-v", help="Print what the script is doing (default: %(default)s)",
                    action="store_true", required=False, default=False)
args = parser.parse_args()

""" Configuring the logger """
logging.basicConfig(filename=args.log + ".log", filemode="w", level=logging.DEBUG,
                    format=f"[%(asctime)s | {args.out} ]  %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")
if args.verbose:
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(f"[%(asctime)s | {args.out} ] %(message)s")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

""" Check for command line arguments """
error = f"""Not enough arguments! The script requires either both read files and/or a genome assembly file.
Run {parser.prog} -h to see usage."""
Ref.analysis_path = ""
if not args.a:
    # assembly file is not supplied, make sure both reads file are supplied
    if not args.r1 or not args.r2:
        logging.critical(f"Error: {error}")
        sys.exit(1)
    Ref.analysis_path = "r"
    logging.info("User supplied both read files, will adopt the assembly/mapping/alignment paradigm")
elif args.r1:
    # assembly is supplied, do we have reads1?
    Ref.analysis_path = "a"
    if args.r2:
        # we have reads and assembly
        Ref.analysis_path += "r"
        logging.info("User supplied both read files and the assembly file, will adopt the mapping/alignment paradigm")
    else:
        # reads2 is missing, which is incorrect
        logging.critical(f"Error: {error}")
        sys.exit(1)
else:
    # assembly is supplied, read1 is not. Is read2 supplied?
    Ref.analysis_path = "a"
    if args.r2:
        # only reads2 is supplied, which is incorrect
        logging.critical(f"Error: {error}")
        sys.exit(1)
    logging.info("User supplied the assembly file, will adopt the alignment/in silico pcr paradigm")

""" Check for files, folders and dependencies in environment """


# TODO: check if the dependency programs are installed
def check_program(program_name: str) -> None:
    # Check for bwa
    # Check for sambamba
    # Check for freebayes
    # Check for samtools
    # Check for BLAST (blastn and makeblastdb)
    # Check for isPcr -> packaged with this script
    logging.info(f"Checking for program {program_name}")
    pass


def check_files() -> None:
    """Checks if all the input files exists, exits if file not found or if file is a directory

    Returns
    -------
    None
        Exits the program if file doesn't exist
    """
    if args.r1 and not os.path.isfile(args.r1):
        logging.critical(f"Read file 1: '{args.r1}' doesn't exist. Exiting")
        sys.exit(1)
    if args.r2 and not os.path.isfile(args.r2):
        logging.critical(f"Read file 2: '{args.r2}' doesn't exist. Exiting")
        sys.exit(1)
    if args.a and not os.path.isfile(args.a):
        logging.critical(f"Assembly file: '{args.a}' doesn't exist. Exiting")
        sys.exit(1)
    if os.path.isdir(args.out):
        if args.overwrite:
            logging.info(f"Output directory exists, removing the existing directory")
            # TODO: implement try-catch
            shutil.rmtree(args.out)
            os.mkdir(args.out)
            logging.info(f"New output directory created")
        else:
            logging.critical(f"Output directory '{args.out}' exists and overwrite is turned off. Exiting")
            sys.exit(1)
    else:
        os.mkdir(args.out)
        logging.info(f"New output directory created")
    if not os.path.isdir(args.sbt):
        logging.critical(f"SBT directory: '{args.a}' doesn't exist. Exiting")
        sys.exit(1)
    for locus in Ref.locus_order:
        file = os.path.join(args.sbt, locus + args.suffix)
        if not os.path.isfile(file):
            logging.critical(f"Allele file: '{file}' for locus ({locus}) doesn't exist. Exiting")
            sys.exit(1)


def ensure_safe_threads(threads: int = args.t) -> None:
    """Ensures that the number of user supplied threads doesn't exceed system capacity

    Sets the number of threads to maximum available threads if threads exceed system capacity.

    Parameters
    ----------
    threads : int
        Number of threads supplied by the user.

    Returns
    -------
    None
        Threads are adjusted, no value is returned

    """
    if threads > multiprocessing.cpu_count():
        logging.critical("User has supplied more threads than processor capacity, resetting to max cores.")
        args.t = multiprocessing.cpu_count()


""" Functions """


# TODO: implement try-catch for running programs
def run_command(command: str, tool: str, stdin: str = None) -> str:
    """Runs a command, and logs it nicely

    Wraps around logging and subprocess.check_output

    Parameters
    ----------
    command : str
        The command to be executed. Converted to a list internally.

    tool: str
        The name of the tool for logging purposes

    stdin: str, optional
        Optional text to be supplied as stdin to the command

    Returns
    -------
    str
        The output generated by running the command

    """
    logging.debug(f"Running command: {command}")
    logging.info(f"Running {tool}")
    # result = ""
    if stdin is not None:
        result = subprocess.check_output(command.split(" "), stderr=subprocess.STDOUT,
                                         input=bytes(stdin, "utf-8")).decode("utf-8")
    else:
        result = subprocess.check_output(command.split(" "), stderr=subprocess.STDOUT).decode("utf-8")
    logging.debug(f"Command log for {tool}:\n{result}")
    logging.info(f"Finished running {tool}")
    return result


# TODO: add a checkpoint
def add_checkpoint(step: str) -> None:
    pass


# TODO: check if checkpoint exists
def check_checkpoint(step):
    pass


# TODO: resume a run from checkpoint
def resume_checkpoint(step):
    pass


# TODO: Create the file and indices inside the args.out folder
def validate_ref() -> None:
    """Checks if the reference files and indices exist, creates them otherwise, returns nothing

    Returns
    -------
    None
        FASTA file, bwa index and faidx index are created if they don't exist, nothing is returned

    """
    if not os.path.isfile(Ref.file):
        logging.info("Reference fasta file doesn't exist, creating now")
        with open(Ref.file, "w") as f:
            f.write(f">{Ref.name}\n{Ref.seq}\n")

    if not os.path.isfile(Ref.file + ".bwt"):
        logging.info("Reference fasta index doesn't exist, creating now")
        run_command(f"bwa index {Ref.file}", "bwa index")
        run_command(f"samtools faidx {Ref.file}", "samtools faidx")


def check_coverage(file: str, min_depth: int = args.d) -> bool:
    """Checks if sufficient read coverage is present throughout the reference gene

    Parameters
    ----------
    file : str
        BAM file to be processed for coverage

    min_depth: int, optional
        Minimum depth to be checked against

    Returns
    -------
    bool
        returns True if all positions have coverage above minimum, False otherwise
    """
    logging.info(f"Computing coverage for {file}")
    depth = subprocess.check_output(
        f"samtools depth -a -r {Ref.name}:{Ref.allele_start}-{Ref.allele_stop} {file}".split(" ")).decode(
        "utf-8").split("\n")
    for d in depth:
        d = d.rstrip().split("\t")
        if len(d) < 3:
            break
        if int(d[2]) < min_depth:
            logging.warning(f"Low depth base (depth={d[2]}) found in {file}, at pos {d[0]}:{d[1]}.")
            return False

    logging.info(f"File {file} passes depth check.")
    return True


def call_variants(prefix: str) -> bool:
    """Call variants from SAM file

    Goes through the following steps:
    1. SAM to BAM (sambamba)
    2. sort SAM (sambamba)
    3. call variants using Freebayes
    4. check_coverage

    Parameters
    ----------
    prefix : str
        prefix of the SAM file

    Returns
    -------
    bool
        returns True if all positions in the alignment have read coverage above minimum, False otherwise
    """
    # SAM -> BAM and sort
    sam2bam = f"sambamba view -f bam -S -t {args.t} -o {prefix}.bam {prefix}.sam"
    run_command(sam2bam, "sambamba SAM to BAM conversion")

    sort_bam = f"sambamba sort -t {args.t} {prefix}.bam"
    run_command(sort_bam, "sambamba sort BAM")

    # Call variants
    freebayes_call = f"freebayes -v {prefix}.vcf -f {Ref.file} {prefix}.sorted.bam"
    run_command(freebayes_call, "freebayes")

    # Check that there is coverage across the entire gene region
    return check_coverage(file=f"{prefix}.sorted.bam")


def filter_sam_file(samfile: str, outfile: str) -> None:
    """Creates SAM files for full set and filtered set

    Full set = SAM generated using all the reads data
    Fultered set = Reads are subsetted to only include reads originating from mompS2, SAM file is generated from them

    Parameters
    ----------
    samfile : str
        SAM file to be processed for coverage

    outfile : str
        name of the output file

    Returns
    -------
    None
        End points are SAM files
    """
    # find proper read pairs
    proper_pairs = f"samtools view -h -f 0x2 {samfile}"
    proper_pairs = run_command(proper_pairs, "samtools view").rstrip().split("\n")

    reads_of_interest = {}  # this dict will hold the read IDs that are in the mompS2 gene
    header_text = ""  # header text to be printed as is in the output file
    all_reads = {}  # this dict will hold all the reads in the input file
    for line in proper_pairs:
        if line.startswith("@"):
            header_text += line + "\n"
            continue
        cols = line.rstrip().split("\t")
        read_id = cols[0]
        read_start = int(cols[3])

        if read_id in all_reads:
            all_reads[read_id] += line
        else:
            all_reads[read_id] = line

        region_start = Ref.flank_start
        # TODO: Improve region_end calculation
        # region_end is a way to check that one of the pair is in the right flank.
        # a better way of checking this will be to look at the right-most mapping position
        region_end = Ref.flank_stop - int(re.search(r"\d+M", cols[5]).group()[:-1])
        if read_start < region_start or read_start > region_end:
            reads_of_interest[read_id] = 1

    with open(outfile, "w") as fh:
        fh.write(header_text)
        for row in all_reads:
            if row in reads_of_interest:
                fh.write(all_reads[row] + "\n")


def vcf_to_fasta(full_vcf: str, filtered_vcf: str) -> str:
    """Creates a sequence out of the VCF file

    Processes the VCF file and make changes to the reference allele according to the variants discovered in
    VCF file.

    Parameters
    ----------
    full_vcf : str
        VCF file generated from the full read set

    filtered_vcf : str
        VCF file generated from the filtered mompS2 specific read set/SAM file. Used to resolve conflicting calls.

    Returns
    -------
    str
        Gene sequence (not the allele) as constructued from the two vcf files
    """
    this_seq = ""
    start_anchor = 0

    filtered_call = {}
    with open(filtered_vcf, "r") as f:
        logging.debug("Reading in filtered VCF file")
        for line in f:
            if line.startswith("#"):
                continue
            (_, pos, _, ref, alt, _, _, info, _, gt) = line.rstrip().split("\t")
            pos = int(pos)
            # TODO: implement try-catch for scenario when ab can not be converted to float
            ab = float(re.search("AB=[0-9.,]+;", info).group()[3:-1])
            # if ab == 0:
            # homozygous call
            filtered_call[pos] = alt
            filtered_call[f"{pos}_ab"] = ab
            logging.debug(f"Added {alt} at pos {pos}")

    with open(full_vcf, "r") as f:
        logging.debug(f"Detailed track of changes from VCF to FASTA")
        for line in f:
            if line.startswith("#"):
                continue
            (_, pos, _, ref, alt, _, _, info, _, gt) = line.rstrip().split("\t")
            pos = int(pos)
            # check if this position is within the typing allele
            if Ref.allele_start <= pos <= Ref.allele_stop:
                # check for zygosity
                ab = re.search("AB=[0-9.,]+;", info).group()[3:-1]
                logging.debug(f"looking for pos {pos} with ab = {ab}")
                if re.search(",", ab) or float(ab) != 0:
                    # heterozygous call
                    # Two scenarios:
                    # 1. POS exist in filtered file          => add the alternative base from filtered_vcf
                    # 2. POS doesn't exist in filtered file  => add the reference base
                    if pos in filtered_call:
                        if re.search(",", ab):
                            this_seq += Ref.seq[start_anchor:(pos - 1)] + filtered_call[pos]
                            logging.debug(f"block 1.1: {start_anchor}-{pos - 1}: {Ref.seq[start_anchor:(pos - 1)]}")
                            logging.debug(f"block 1.1: {pos}: {ref} to {filtered_call[pos]}")
                            start_anchor = pos - 1 + len(ref)
                        elif filtered_call[f"{pos}_ab"]  == 0 or filtered_call[f"{pos}_ab"] > float(ab):
                            this_seq += Ref.seq[start_anchor:(pos - 1)] + alt
                            logging.debug(f"block 1.2: {start_anchor}-{pos - 1}: {Ref.seq[start_anchor:(pos - 1)]}")
                            logging.debug(f"block 1.2: {pos}: {ref} to {alt}")
                            start_anchor = pos - 1 + len(ref)
                        else:
                            pos -= 1  # 0-based in list
                            this_seq += Ref.seq[start_anchor:pos] + ref
                            logging.debug(f"block 1.3: {start_anchor}-{pos}: {Ref.seq[start_anchor:pos]}")
                            logging.debug(f"block 1.3: {pos}: {ref} stays")
                            start_anchor = pos + len(ref)
                    else:
                        pos -= 1  # 0-based in list
                        this_seq += Ref.seq[start_anchor:pos] + ref
                        logging.debug(f"block 2: {start_anchor}-{pos}: {Ref.seq[start_anchor:pos]}")
                        logging.debug(f"block 2: {pos}: {ref} stays")
                        start_anchor = pos + len(ref)
                else:
                    # homozygous call
                    pos -= 1  # 0-based in list
                    this_seq += Ref.seq[start_anchor:pos] + alt
                    logging.debug(f"block 3: {start_anchor}-{pos}: {Ref.seq[start_anchor:pos]}")
                    logging.debug(f"block 3: {pos}: {ref} to {alt}")
                    start_anchor = pos + len(ref)

    this_seq += Ref.seq[start_anchor:]
    return this_seq


def blast_momps_allele(seq: str, db: str = os.path.join(args.sbt, "mompS" + args.suffix)) -> str:
    """BLAST the mompS allele in the isolate to find the allele number

    Parameters
    ----------
    seq : str
        mompS allele sequence found in the isolate

    db : str, optional
        location of the mompS alleles database file

    Returns
    -------
    str
        mompS allele number
    """
    logging.debug(f"Looking for \n{seq}")
    makeblastdb = f"makeblastdb -in {db} -dbtype nucl"
    run_command(makeblastdb, "makeblastdb/mompS")
    blastcmd = f"blastn -query - -db {db} -outfmt 6 -perc_identity 100"
    res = run_command(blastcmd, "blastn/mompS", seq).rstrip()
    if res == "":
        # TODO: run blast again with lower identity threshold and return allele*
        return "-"
    else:
        cols = res.split("\t")
        allele = cols[1].replace("mompS_", "")
        return allele


def call_momps_mapping(r1: str = args.r1, r2: str = args.r2, outfile: str = os.path.join(args.out, args.prefix),
                       filt_file: str = "") -> str:
    """Finds the mompS allele number using the mapping strategy

    Adopts the mapping based strategy to identify the allele present in the current isolate

    Parameters
    ----------
    r1 : str, optional
        Read1 file name

    r2 : str, optional
        Read2 file name

    outfile : str, optional
        Output prefix

    filt_file : str, optional
        Prefix to be used for filtered SAM and VCF file

    Returns
    -------
    str
        Gene sequence (not the allele) as constructued from the two vcf files
    """
    if filt_file == "":
        filt_file = outfile + ".filtered"

    # Map reads to mompS gene
    bwa_call = f"bwa mem -t {args.t} {Ref.file} {r1} {r2} -o {outfile}.sam"
    run_command(bwa_call, "bwa")

    # Create a separate file containing reads coming from the border regions
    filter_sam_file(samfile=f"{outfile}.sam", outfile=f"{filt_file}.sam")

    # Call variants
    full_coverage = call_variants(prefix=outfile)
    filtered_coverage = call_variants(prefix=filt_file)

    allele_confidence = ""
    if not (full_coverage or filtered_coverage):
        allele_confidence = "?"

    allele_seq = vcf_to_fasta(full_vcf=outfile + ".vcf", filtered_vcf=filt_file + ".vcf")
    allele_seq = allele_seq[(Ref.allele_start - 1):Ref.allele_stop]

    mompS_allele = blast_momps_allele(allele_seq)
    if mompS_allele != "-":
        mompS_allele += allele_confidence

    return mompS_allele


def call_momps_pcr(assembly_file: str = args.a, db: str = os.path.join(args.sbt, "mompS" + args.suffix)) -> str:
    """Find the mompS gene using an in silico PCR procedure

    Parameters
    ----------
    assembly_file : str, optional
        Read1 file name

    db : str, optional
        Read2 file name

    Returns
    -------
    str
        mompS allele number
    """
    makeblastdb = f"makeblastdb -in {db} -dbtype nucl"
    run_command(makeblastdb, "makeblastdb/mompS")
    blast_command = f"blastn -db {db} -outfmt 6 -query {assembly_file} -perc_identity 100"
    res = run_command(blast_command, "blastn/mompS").rstrip().split("\n")
    res = [line.rstrip().split("\t")[1] for line in res]

    alleles = {}
    for allele in res:
        alleles[allele.replace("mompS_", "")] = 1
    alleles = list(alleles.keys())

    if len(alleles) == 1:
        return alleles[0]
    else:
        primer1 = os.path.join(args.out, "mompS_primer1.tab")
        with open(primer1, "w") as f:
            f.write("mompS_1\t" + Ref.mompS_primer1)
        ispcr_command = f"isPcr {assembly_file} {primer1} {Ref.ispcr_opt}"
        primer1_res = run_command(ispcr_command, "mompS2 primer1")

        if primer1_res != "":
            # nested PCR
            primer2 = os.path.join(args.out, "mompS_primer2.tab")
            with open(primer2, "w") as f:
                f.write("mompS_2\t" + Ref.mompS_primer2)
            ispcr_command = f"isPcr stdin {primer2} {Ref.ispcr_opt}"
            primer2_res = run_command(ispcr_command, "mompS2 primer2", primer1_res).rstrip().split("\n")
            primer2_res = "".join(primer2_res[1:])
            logging.debug(f"Found the sequence: {primer2_res}")
            return blast_momps_allele(primer2_res)
        else:
            logging.info("In silico PCR returned no results, try mapping route")
            return "-"


def genome_assembly(r1: str = args.r1, r2: str = args.r2, out: str = os.path.join(args.out, "run_spades")) -> None:
    """Perform de novo genome assembly using spades

    Parameters
    ----------
    r1 : str, optional
        Read1 file name

    r2 : str, optional
        Read2 file name

    out : str, optional
        output directory name for spades

    Returns
    -------
    None
        Executes the commands and exits
    """
    assembly_command = f"spades.py -1 {r1} -2 {r2} -o {out} --careful -t {args.t}"
    run_command(assembly_command, "spades")
    args.a = os.path.join(out, "scaffolds.fasta")


def blast_non_momps(assembly_file: str = args.a) -> dict:
    """Find the rest of alleles (non-mompS) by BLAST search

    Parameters
    ----------
    assembly_file : str, optional
        Read1 file name

    Returns
    -------
    dict
        dictionary containing locus (key) to allele (value) mapping
    """
    loci = ["flaA", "pilE", "asd", "mip", "proA", "neuA_neuAH"]
    calls = {}
    for locus in loci:
        db = os.path.join(args.sbt, locus + args.suffix)
        makeblastdb = f"makeblastdb -in {db} -dbtype nucl"
        run_command(makeblastdb, f"makeblastdb/{locus}")
        blastcmd = f"blastn -query {assembly_file} -db {db} -outfmt 6 -perc_identity 100"
        res = run_command(blastcmd, f"blastn/{locus}").rstrip()
        # allele = ""
        if res == "":
            # TODO: run blast again with lower identity threshold and return allele*
            allele = "-"
        else:
            cols = res.split("\t")
            allele = cols[1].replace(locus + "_", "")
        calls[locus] = allele
    return calls


def get_st(allele_profile: str, profile_file: str = args.profile) -> str:
    """Looks for the ST in the allele profile table (simple look-up)

    Parameters
    ----------
    allele_profile : str, optional
        allele profile as ordered tab-separated string

    profile_file : str, optional
        profile file containing ST as the first column, and allele profiles in the next columns

    Returns
    -------
    str
        ST number
    """
    with open(profile_file, "r") as f:
        f.readline()
        for line in f:
            line = line.rstrip()
            if line.endswith(allele_profile):
                st = line.split("\t")[0]
                return st
    return "-"
    # following system call craps out, will debug it someday
    # allele_profile = allele_profile.replace("\t", "\\t")
    # grep_command = f"grep -P \'{allele_profile}$\' {profile_file}"
    # st = run_command(grep_command, "Retreiving ST").rstrip().split("\t")[0]
    # return st


def choose_analysis_path(header: bool = True) -> str:
    """Pick the correct analysis path based on the program input supplied

    Parameters
    ----------
    header : bool, optional
        should the header be returned in the output

    Returns
    -------
    str
        formatted ST + allele profile (and optional header) of the isolate
    """
    alleles = {}
    if Ref.analysis_path == "ar":
        mompS_allele = call_momps_mapping()
        if mompS_allele == "-":
            mompS_allele = call_momps_pcr()
        alleles = blast_non_momps()
        alleles["mompS"] = mompS_allele
    elif Ref.analysis_path == "a":
        alleles = blast_non_momps()
        alleles["mompS"] = call_momps_pcr()
    elif Ref.analysis_path == "r":
        genome_assembly()
        mompS_allele = call_momps_mapping()
        if mompS_allele == "-":
            mompS_allele = call_momps_pcr()
        alleles = blast_non_momps()
        alleles["mompS"] = mompS_allele
    else:
        logging.critical("This path should not have been traversed. Is Ref.analysis_path being changed somewhere else?")

    return print_table(alleles, header)


def print_table(alleles: dict, header: bool = True) -> str:
    """Formats the allele profile so it's ready for printing

    Parameters
    ----------
    alleles : dict
        The allele profile and the ST

    header : bool, optional
        should the header be returned in the output

    Returns
    -------
    str
        formatted ST + allele profile (and optional header) of the isolate
    """
    allele_profile = ""
    for locus in Ref.locus_order:
        allele_profile += alleles[locus] + "\t"
    allele_profile = allele_profile.rstrip()
    allele_profile = get_st(allele_profile) + "\t" + allele_profile

    head = "ST\t" + "\t".join(Ref.locus_order) + "\n"
    if header:
        return head + allele_profile
    else:
        return allele_profile


def pretty_time_delta(seconds: int):
    """Pretty print the time

    Parameters
    ----------
    seconds : int
        Time in seconds to convert to human readable

    Returns
    -------
    str
        human readable time
    """
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


""" Main code """
logging.info("Starting preprocessing")
logging.info("Checking if all the prerequisite programs are installed")
for program in Ref.prereq_programs:
    check_program(program)
logging.info("All prerequisite programs are accessible")

logging.info("Checking if all the required input files exist")
check_files()
logging.info("Input files are present")

logging.info("Ensuring thread counts are correct")
ensure_safe_threads()
logging.info("Thread count has been validated")

logging.info("Checking for reference files")
validate_ref()
logging.info("All reference files have been discovered")

logging.info("Checking for reference files")
output = choose_analysis_path()
logging.info("Finished analysis")

logging.debug(f"Output = \n{output}\n")
print(output)

total_time = pretty_time_delta(int(time.time() - t0))
logging.info(f"The program took {total_time}")
