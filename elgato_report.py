#!/usr/bin/env python3

import sys
import json
import math
import argparse
from dataclasses import dataclass
from datetime import date
from fpdf import FPDF
from ctypes import alignment

LOGO="""\
 /\\_/\\  
( o.o ) 
 > ^ <\
"""

summary_header = """\
Sequence Based Typing (SBT) is based on 7 __Legionella pneumophila__ loci (__flaA__, __pilE__, __asd__, \
__mip__, __mompS__, __proA__, __neuA/neuAh__). Each locus is assigned an allele number based on comparison \
of its sequence with sequences in an allele database. The allelic profile is the combination of allele \
numbers for all seven loci in order and denotes a unique Sequence Type (ST). el_gato utilizes either a \
genome assembly (.fasta) or Illumina paired-end reads (.fastq) to accomplish __Legionella pneumophila__ SBT.\
More information about each sample can be found in the log file generated by el_gato. While a key to \
the definitions is found on the **Definition Overview** page. \
"""

reads_header = """\
The following sample was analyzed using the paired-end reads functionality with el_gato version {}. The tables below show the full \
ST profile of the sample, the coverage data for each locus, and information regarding the primers used to \
identify the primary mompS allele. Low depth bases indicate bases that do not have 10 or more reads covering \
that base, unless the default depth cutoff was adjusted. More information can be found in the log file for this sample. \
"""

assembly_header = """\
The following sample was analyzed using the assembly functionality with el_gato version {}. The tables below show the full \
ST profile of the sample and the corresponding locus location information. Unless specified by the user, \
el_gato utilizes a default 30% (0.3) BLAST hit length threshold and a 95% (95.0) sequence identity threshold \
to identify the presence of multiple copies of an allele. el_gato will only report allele matches for BLAST hits \
of 100% length and 100% identity. More information can be found in the log file for this sample. \
"""

default_report_header = """\
El_gato Reports
Used for Batch and Sample-Level Summaries
https://github.com/CDCgov/el_gato
Developed by Applied Bioinformatics Laboratory
(ABiL)\
"""

abbrev_key = """\
Novel ST = the alleles for all 7 loci were identified, however their unique combination and corresponding ST has not been found in the database. \n
Novel ST* = an exact match for sequences of at least one locus was not identified in the database, which may indicate a novel allele. \n
MA? = **m**ultiple **a**lleles; for at least one locus, multiple alleles were identified, and the true allele could not be resolved; therefore, no ST could be determined. \n
MD- = **m**issing **d**ata; data were missing for at least one locus (e.g., low read coverage at one or more position, missing sequence in assembly); therefore, no ST could be determined. \n
'-' = missing data; data were missing for this locus (e.g., low read coverage at one or more position, missing sequence in assembly); therefore, an allele number could not be determined. \n
'NAT' = **n**ovel **a**llele **t**ype; this locus did not match any allele listed in the database, possibly indicating a novel allele. \n
'?' = multiple alleles; for this locus multiple alleles were identified, and could not be resolved.\
"""

primer_footer = """\
Multiple __mompS__ alleles may be identified in the genome of a single __L. pneumophila__ isolate. In these instances, \
it is important to use the correct mompS allele to generate the allelic profile and ST. el_gato resolves this issue by \
considering the orientation of a small "primer" sequence in relation to the reference sequence. Please see the el_gato \
README for more details.

"NA" indicates that primer support was not assessed since only one mompS allele was identified. Otherwise, the primary mompS allele is identified using the following criteria: \n
1. Only one allele has associated reads with the correctly oriented primer. \n
2. One allele has more than 3 times as many reads with the correctly oriented primer as the other. \n
3. One allele has no associated reads with the primer in either orientation, but the other has reads with the primer only in the wrong direction. The sequence with no associated reads is considered the primary locus in this case. \n
4. Absence of any primer-associated reads does not allow identification of the primary allele.\
"""
primer_footer2 = """\
Please find the key for definitions and evidence for support of __mompS__ allele call \
on the Definitions Overview page.
"""

github_url = """ \
https://github.com/CDCgov/el_gato \
"""

@dataclass
class Report(FPDF):
	sample_id: str
	st: str
	flaA: str
	pilE: str
	asd: str
	mip: str
	mompS: str
	proA: str
	neuA_neuAH: str
	mode: str
	mode_specific: dict
	version: str
	shorten_names: bool=False
	
	@classmethod
	def from_json(cls, json_data, shorten_names=False):
		sample_id = json_data["id"]
		st = json_data["mlst"]["st"]
		flaA = json_data["mlst"]["flaA"]
		pilE = json_data["mlst"]["pilE"]
		asd = json_data["mlst"]["asd"]
		mip = json_data["mlst"]["mip"]
		mompS = json_data["mlst"]["mompS"]
		proA = json_data["mlst"]["proA"]
		neuA_neuAH = json_data["mlst"]["neuA_neuAH"]
		mode = json_data["operation_mode"]
		mode_specific = json_data["mode_specific"]
		version = json_data.get("version", "UNKNOWN")
		x = cls(
			sample_id,
			st,
			flaA,
			pilE,
			asd,
			mip,
			mompS,
			proA,
			neuA_neuAH,
			mode,
			mode_specific,
			version,
			shorten_names,
			
		)
		return x

	def list_mlst(self):
		sample_id = self.sample_id
		if self.shorten_names:
			if len(self.sample_id) > 23:
				sample_id = self.sample_id[:20] + "..."
		return [
			sample_id,
			self.st,
			self.flaA,
			self.pilE,
			self.asd,
			self.mip,
			self.mompS,
			self.proA,
			self.neuA_neuAH
			]

	def sample_report(
		self,
		pdf,
		typeface='Courier',
		body_style='',
		body_size=11,
		head_style='B',
		head_size=16
		):

		pdf.add_page()
		pdf.set_font(typeface, head_style, head_size)

		if self.mode == "Assembly":
			pdf = self.assembly_report(pdf, typeface, body_style, body_size)
		elif self.mode == "Reads":
			pdf = self.reads_report(pdf, typeface, body_style, body_size)
		else:
			sys.exit(
				f"Unsupported operation mode identified for sample {self.sample_id}"
				)
		return pdf

	def reads_report(self, pdf, typeface, style, size):
		pdf.set_font(typeface, style, size)
		pdf.set_font('Courier', 'B', 10)
		pdf.multi_cell(
			h=4,w=0,
			text="--E--pidemiology of __--L--egionella__: --G--enome-b--A--sed --T--yping (el_gato) Paired-End Reads Report",
			align="C",
			markdown=True
		)
		pdf.ln(10)
		pdf.set_font('Courier', '', 11)
		pdf.multi_cell(
			h=4, w=0,
			text=f"**{self.sample_id} reads report**",
			align="L",
			markdown=True
		)
		pdf.ln(2)
		pdf.multi_cell(
			w=0,h=5,
			text=reads_header.format(self.version),
			new_x="LMARGIN", new_y="NEXT"
			)
		pdf.ln(8)

		pdf = self.make_mlst_table(pdf, [self.list_mlst()], self.shorten_names)
		pdf.ln(6)

		pdf.set_font(style="BU")
		pdf.cell(
			w=0,h=10,
			text=f"Locus Information",
			new_x="LMARGIN", new_y="NEXT", align="C"
			)

		pdf.set_font()
		pdf = self.read_coverage_table(pdf)

		pdf.ln(6)
		pdf.set_font(style="BU")
		pdf.cell(
			w=0,h=10,
			text=f"__mompS__ Primer Information",
			new_x="LMARGIN", new_y="NEXT", align="C",
			markdown=True)
		pdf.set_font()
		pdf = self.mompS_primer_table(pdf)
		pdf.multi_cell(w=0, h=3.5, 
		text=primer_footer2,
		new_x="LMARGIN", new_y="NEXT", 
		markdown=True)
		return pdf


	def read_coverage_table(self, pdf):
		contents = [["Locus", "Percent Covered", "Mean Depth", "Minimum Depth", "Low depth bases"]]
		contents += [
			[
				k,
				f'{float(v["Percent_covered"]):.1f}' if "Percent_covered" in v else "-",
				f'{float(v["Mean_depth"]):.1f}' if "Mean_depth" in v else "-",
				f'{float(v["Min_depth"]):.1f}' if "Min_depth" in v else "-",
				f'{float(v["Num_below_min_depth"]):.1f}' if "Num_below_min_depth" in v else "-"
			] for k, v in self.mode_specific["locus_coverage"].items()]
		col_widths = (37.5, 37.5, 37.5, 37.5, 37.5)
		alignment = ("CENTER", "CENTER", "CENTER", "CENTER", "CENTER")

		pdf = self.make_table(
			pdf,
			contents,
			col_widths=col_widths,
			text_align=alignment
			)

		return pdf

	def mompS_primer_table(self, pdf):
		contents = [["Allele", "Reads Indicating Primary", "Reads Indicating Secondary"]]
		# Report no reads supporting either if the run failed and didn't output a reads result
		null_primer_result = [["mompS_-", "0", "0"]]
		contents += self.mode_specific.get("mompS_primers", null_primer_result)
		col_widths = (50, 50, 50)
		alignment = ("CENTER", "CENTER", "CENTER")

		pdf = self.make_table(
			pdf,
			contents,
			col_widths=col_widths,
			text_align=alignment
			)
		pdf.ln(2)

		return pdf

	def assembly_report(self, pdf, typeface, style, size):
		pdf.set_font(typeface, style, size)
		pdf.set_font('Courier', 'B', 10)
		pdf.multi_cell(
			h=4,w=0,
			text="--E--pidemiology of __--L--egionella__: --G--enome-b--A--sed --T--yping (el_gato) Assembly Results",
			align="C",
			markdown=True
		)
		pdf.ln(10)
		pdf.set_font('Courier', '', 11)
		pdf.set_font(style="U")
		pdf.multi_cell(
			h=4, w=0,
			text=f"**{self.sample_id.replace('_',' ')} genomic report**",
			align="L",
			markdown=True
		)
		pdf.set_font()
		pdf.ln(2)
		pdf.multi_cell(
			w=0,h=5,
			text=assembly_header.format(self.version),
			new_x="LMARGIN", new_y="NEXT"
			)
		pdf.ln(10)
		pdf = self.make_mlst_table(pdf, [self.list_mlst()], self.shorten_names)
		pdf.ln(8)

		pdf.set_font(style="BU")
		pdf.cell(
			w=0,h=10,
			text=f"Locus Information",
			new_x="LMARGIN", new_y="NEXT", align="C"
			)
		pdf.set_font()
		pdf = self.locus_location_table(pdf)

		return pdf

	def locus_location_table(self, pdf):
		header = [["locus", "allele", "contig", "start", "stop", "%length"]]
		contents = []
		x = 1
		for k, v in self.mode_specific["BLAST_hit_locations"].items():
			for row in v:
				# set % length
				p_length = 100*(int(row[-2])-int(row[-3])+1)/int(row[-1])
				row[-1] = (f"{p_length:.1f}")
				# shorten contig names if needed
				if self.shorten_names:
					if len(row[1]) > 28:
						row[1] = row[1][:25] + "..."

			contents.append([k] + v[0])
			if len(v) > 1:
				for row in v[1:]:
					contents.append([""] + row)

		col_widths = (20, 30, 50, 15, 15, 15)
		alignment = ("CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER")

		content = [i for i in contents]

		# if shortening names, don't adjust table for long lines
		if self.shorten_names:
			chars = 1000
		else:
			chars = 25
		batches = self.fit_table(pdf, content, pdf.get_y(), chars)
		# Add a header to each table
		for i in range(len(batches)):
			batches[i] = header + batches[i]
		pdf = self.make_table(
			pdf,
			batches[0],
			col_widths=col_widths,
			text_align=alignment
			)
		if len(batches) > 1:
			for batch in batches[1:]:
				pdf.add_page()
				pdf.set_y(pdf.get_y() + 10)
				pdf = self.make_table(
					pdf,
					batch,
					col_widths=col_widths,
					text_align=alignment
				)
		
		pdf.ln(4)
		pdf.cell(
			w=0,h=2,
			text=r"% Length = BLAST hit length as a percent of expected locus size.",
			new_x="LMARGIN", new_y="NEXT"
		)

		return pdf

	def split_highlight_batches(self, batches, highlight_rows):
		highlight_list = []
		for batch in batches:
			size = len(batch)
			highlight_list.append(set([i for i in highlight_rows if i <= size]))
			highlight_rows = [i-size for i in highlight_rows if i-size > 0]
		return highlight_list

	@staticmethod
	def make_table(pdf, data, col_widths=None, text_align=None, highlight_rows=set()):
		with pdf.table(
			col_widths=col_widths,
			text_align=text_align,
		) as table:
			for n, data_row in enumerate(data):
				row = table.row()
				if n in highlight_rows:
					pdf.set_fill_color(243, 177, 170)
				else:
					pdf.set_fill_color(0, 0, 0)
				for item in data_row:
					row.cell(item)
			pdf.set_fill_color(0, 0, 0)
			return pdf
	
	@staticmethod
	def fit_table(pdf, data, initial_y, characters:int):
		font_size = pdf.font_size
		pdf_y = initial_y
		n = 0
		max_length = 0
		batches = []
		this_batch = []
		while n < len(data):
			row = data[n]
			for i in row:
				column_length = len(i)
				if column_length > max_length:
					max_length = column_length
			num_lines = math.ceil(max_length / characters)
			cell_height = 2* num_lines * font_size
			if pdf_y + cell_height + 10 > pdf.page_break_trigger:
				batches.append(this_batch)
				this_batch = [row]
				n+=1
				pdf_y = pdf.head_spacing # Whatever we want the starting y position to be on a new page
				continue

			n+=1
			pdf_y += cell_height
			this_batch.append(row)
		batches.append(this_batch)
		return batches		

	@staticmethod
	def make_mlst_table(pdf, data, shorten_names=False):
		contents = [["Sample ID","ST","flaA","pilE","asd","mip","mompS","proA","neuA"]]
		for sample in data:
			if shorten_names:
				# Make sure sample id is fewer than XXX characters
				s_name = sample[0]
				if len(s_name) > 23:
					sample[0] = s_name[0:20] + "..."
			contents.append(sample)
		col_widths = (60, 18, 18, 18, 18, 18, 18, 18, 18)
		alignment = ("CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER")
		pdf = Report.make_table(pdf, contents, col_widths=col_widths, text_align=alignment)
		return pdf

	@staticmethod
	def read_jsons(files, shorten_names=False):
		data = []
		for file in files:
			with open(file) as fin:
				json_data = json.load(fin)
				data.append(Report.from_json(json_data, shorten_names))
		return data
	
	@staticmethod
	def read_multi_json(files, shorten_names=False):
		data = []
		with open(files) as fin:
			json_data = json.load(fin)
			for i in json_data:
				data.append(Report.from_json(i, shorten_names))
				
		return data	

class PDF_no_header(FPDF):
	def __init__(self, disclaimer_file=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.head_spacing = 0
		self.disclaimer = disclaimer_file
	def footer(self):
		if self.disclaimer:
			# Position cursor at 3 cm from bottom:
			self.set_y(-30)
			# Setting font:
		self.set_font("Courier", "", 8)
		self.multi_cell(0, None, self.disclaimer, align="C")
		# Position cursor at 1.5 cm from bottom:
		self.set_y(-15)
		# Setting font:
		self.set_font("Courier", "", 8)
		 # Print Date (left-aligned)
		self.cell(0, 10, f"{date.today().isoformat()}", align="L")

		# Center the URL
		url_width = self.get_string_width(github_url)  # Get width of the URL text
		page_width = self.w  # Get the width of the page
		left_margin = self.l_margin  # Left margin
		right_margin = self.r_margin  # Right margin
		cell_width = page_width - left_margin - right_margin  # Width available for the URL

		# Calculate the X position to center the URL
		x_centered = (cell_width - url_width) / 2 + left_margin

		# Set the X position for the centered URL
		self.set_x(x_centered)

		# Print the URL (centered)
		self.cell(url_width, 10, f"{github_url}", align="C")

		# Print the page number (right-aligned)
		self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")

class PDF_with_header(PDF_no_header):
	def __init__(self, header_text="", *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.header_text = header_text
		self.head_spacing = self.calc_head_size()

	def header(self):
		self.set_font('Courier', '', 10)
		self.multi_cell(h=3, w=0, text=self.header_text, align="C")
		self.ln(2)

	def calc_head_size(self):
		header_lines = self.header_text.split("\n")
		newlines = len(header_lines) - 1

		for line in header_lines:
			if len(line) < 91:
				continue
			newlines += len(line) // 91\
			
		return newlines * 5

help_message= """
usage: elgato_report.py [-h] -i INPUT_JSONS [INPUT_JSONS ...] -o OUT_REPORT [-s]

options:
  -h, --help            show this help message and exit
  -i, --input_jsons     path to one or more report.json files
  -o, --out_report      desired output pdf file path
  -s, --shorten_names   shorten long sample and contig names to prevent line wrapping
  -n, --no_header       Do not include the header in the report
  -d,  --disclaimer_file     Include disclaimer in footer
  --custom_header       Provide custom header as string in your command
  --header_file         Provide custom header in a text file
"""

class Parser(argparse.ArgumentParser):
	"""Custom class to allow complete control over help message"""
	def print_help(self):
		print(help_message)

def parse_args():
	p = Parser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		add_help=False
	)
	p.add_argument(
		"-i", "--input_jsons",
		required=True,
		nargs="+",
		help="path to one or more report.json files"
	)	
	p.add_argument(
		"-o", "--out_report",
		required=True,
		help="desired output pdf file path"
	)
	p.add_argument(
		"-s", "--shorten_names",
		required=False,
		help="shorten long sample and contig names to prevent line wrapping",
		action="store_true"
	)
	p.add_argument(
		"-n", "--no_header",
		required=False,
		help="Do not include the header in the report",
		action="store_true"
	)
	p.add_argument(
		"-d", "--disclaimer_file",
		required=False,
		help="Include disclaimer in footer"
	)
	p.add_argument(
		"--custom_header",
		required=False,
		type=str,
		help="Provide custom header as string in your command"
	)
	p.add_argument(
		"--header_file",
		required=False,
		help="Provide custom header in a text file"
	)
	p.add_argument(
		"-h", "--help",
		action="help"
	)

	return p.parse_args()

def main():
	args = parse_args()
	if args.custom_header and args.header_file:
		sys.exit("ERROR: You provided both a header file and a header string.\nPlease only provide one of a header file or a header string.")

	# Load input JSONs
	with open(args.input_jsons[0]) as fin:
		if fin.read().startswith("["):
			data = Report.read_multi_json(args.input_jsons[0], args.shorten_names)
		else:
			data = Report.read_jsons(args.input_jsons, args.shorten_names)

	report_header = default_report_header
	if args.custom_header:
		report_header = args.custom_header.encode("utf-8").decode('unicode_escape')
	if args.header_file:
		with open(args.header_file) as fin:
			report_header = fin.read()

	# Check if disclaimer should be included
	if args.disclaimer_file:
		with open(args.disclaimer_file) as fin:
			report_disclaimer = fin.read()
	else:
		report_disclaimer = None

	# Create PDF with or without header and disclaimer
	if args.no_header and report_disclaimer is None:
		pdf = PDF_no_header('', 'P', 'mm', 'Letter')  # No header, no disclaimer
	elif args.no_header and report_disclaimer:
		pdf = PDF_no_header(report_disclaimer, 'P', 'mm', 'Letter')  # No header, yes disclaimer
	elif not args.no_header and report_disclaimer:
		pdf = PDF_with_header(report_header, report_disclaimer, 'P', 'mm', 'Letter')  # Yes header, yes disclaimer
	else:
		pdf = PDF_with_header(report_header, '', 'P', 'mm', 'Letter')  # Yes header, no disclaimer
		
	pdf.add_page()
	pdf.set_font('Courier', 'B', 10)
	pdf.multi_cell(
		h=4, w=0,
		text="--E--pidemiology of __--L--egionella__: --G--enome-b--A--sed --T--yping (el_gato) Batch Results Report",
		align="C",
		markdown=True
	)
	pdf.ln(10)
	pdf.set_font('Courier', '', 16)
	pdf.multi_cell(w=0,h=6, text=LOGO, new_x="LMARGIN", new_y="NEXT")
	pdf.ln(5)
	pdf.set_font('Courier', '', 11)
	pdf.set_font(style="U")
	pdf.multi_cell(
		h=4, w=0,
		text="**Report Summary**",
		align="L",
		markdown=True
	)
	pdf.set_font()
	pdf.ln(5)
	pdf.multi_cell(w=0,h=5, text=summary_header, new_x="LMARGIN", new_y="NEXT",
				   markdown=True)
	pdf.ln(10)
	
	content = [i.list_mlst() for i in data]
	# if shortening names, don't adjust table for long lines
	if args.shorten_names:
		chars = 1000
	else:
		chars = 19
	batches = Report.fit_table(pdf, content, pdf.get_y(), chars)
	for batch in batches:
		if batch != batches[-1]:
			pdf.set_font('Courier', '', 11)
			pdf = Report.make_mlst_table(pdf, batch, args.shorten_names)
			pdf.add_page()
			pdf.ln(10)
		else:
			pdf.set_font('Courier', '', 11)
			pdf = Report.make_mlst_table(pdf, batch, args.shorten_names)
			pdf.ln(5)
	if pdf.get_y() + 50 > pdf.page_break_trigger:
		pdf.add_page()
		pdf.ln(10)

	pdf.add_page()
	pdf.ln(5)
	pdf.set_font(style="BU")
	pdf.cell(w=0,h=0, text="Definitions Overview", new_x="LMARGIN", new_y="NEXT")
	pdf.ln(15)
	pdf.set_font(style="U")
	pdf.cell(w=0,h=0, text="ST Definitions Key", new_x="LMARGIN", new_y="NEXT")
	pdf.ln(5)
	pdf.set_font()
	pdf.multi_cell(w=0,h=3.5, text=abbrev_key, new_x="LMARGIN", new_y="NEXT", markdown=True)
	pdf.ln(15)
	pdf.set_font(style="U")
	pdf.cell(w=0,h=0, text="Evidence for support of __mompS__ allele call", new_x="LMARGIN", new_y="NEXT", markdown=True)
	pdf.ln(5)
	pdf.set_font()
	pdf.multi_cell(w=0, h=3.5, text=primer_footer,new_x="LMARGIN", new_y="NEXT",
	markdown=True)

	for datum in data:
		pdf = datum.sample_report(pdf)

	pdf.output(args.out_report)

if __name__ == '__main__':
	main()
