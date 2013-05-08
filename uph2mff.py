#!/usr/bin/env python
"""
	A program to convert the file format from Prentiss Knowlton's music
	format from his Unplayed by Human Hands project into MIDI FIle Format
	
	The program scans the file, character by character, building a song, which 
	is a list of events.  Events can be notes, tempo changes, comments or 
	whatever else maps to MFF events.  Once built, the program processes
	the events and outputs an MFF file.

	Included in this project:
		parse.py		steps through the file, creating events on the fly
		songevents.py	Classes for the song and events
		key.py			methods for handling the key adjustment of notes
		MFF.py			classes specific to the MIDI File Format
"""

import sys

from optparse import OptionParser


import parse
import songevents


#    a few utils...

def getoptions():
	"""
	standard option parse:
		-f, --file 	input file
		-o, --output	output file (optional, else input file: .uph -> .mid)
		-t, --text text output, Division, Rank, and Orchestration data
	"""
	parser = OptionParser()
	default="None"
	default="Content/test.uph"	# RBF - temporary

	parser.add_option("-f", "--file", dest="filename", action="store",
	type="string", metavar="InputFilename", help="uph data file", default=default)

	parser.add_option("-o", "--outputfile", dest="outfilename", action="store",
	type="string", metavar="OutputFilename", help="MFF data file", default=default)
	
	parser.add_option("-t", "--textfile", dest="textfilename", action="store",
	type="string", metavar="TextSummaryFilename", help="Division, Rank ,and Orchestration Summary file", default=default)

	parser.add_option("-p", "--ppq", dest="PPQ", action="store",
	type="int", metavar="PPQ", help="pulses per quarter note [192]", default=192)
	
	parser.add_option("-c", "--correction", dest="time_correction_factor", action="store",
	type="float", metavar="time_corr", help="Time correction: >1 is longer time, slower tempo", default=1)
	
	(options, args) = parser.parse_args()


	if options.filename == 'None':
		print "Must specify a filename."
		sys.exit(1)

	return (options, args)


def main():
	"""
	main: runstring options, parse the file to a song, output song to a file.
	"""
	
	(options, args) = getoptions()
	f_name=options.filename
	out_name=options.outfilename
	txt_name=options.textfilename
	

	# Set up a Song class - basically as list of events and a way to list them
	song = songevents.Song()
	song.format = 1		# RBF - set from run-string
	song.PPQ = options.PPQ
	print "PPQ:", song.PPQ
	song.time_factor = options.time_correction_factor # stretch or shrink song length
	print "Song.tf", song.time_factor

	# parse the song into a list of events
	parse.parse_song(f_name, song)

	#song.list()	# debug...

	# for testing.  Later:  use option passed file
	outfile = open('testout.mid','wb')

	song.create_MFF(outfile,txt_name)	# create a MIDI file, and optionally, a text summary

	outfile.close()
	
	print "All done."


if __name__ == "__main__":
	main()
