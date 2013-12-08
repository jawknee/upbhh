#!/usr/bin/env python
"""  A quick and dirty attempt to break down a MFF
"""

def value(string):
	i = 0
	for c in string:
		i *= 256
		i += ord(c)
	return(i)

def get_vlq(v):
	i=0

	value = 0
	n = 0x80
	while n & 0x80:	# keep going while the bit is set
		n = ord(v[i])
		value = value << 7
		value += n & 0x7f
		i += 1
	return ( [value, i] )


def main():
	filename="testout.mid"

	file = open(filename, 'r')

	text = file.read()

	total_length=len(text)
	print "Total length:", total_length

	i=0

	while i < total_length:
		header=text[i:i+4]
		i += 4

		lenstr=text[i:i+4]
		i += 4

		length = value(lenstr)
		print "\nheader:", header
		print "length:", length

		print "Content:"

		if header == 'MThd':
			for n in range(length):
				print " %02x" % ord(text[i+n]),
			i += length
			continue
			

		event = text[i:i+length]
		j=0
		while j < length:
			(val, off) = vlq(event[j])
			j += off
		
			event_type = event[j]
			if event_type == 0xff:
				print "Meta-event:"
				etype == event[j+1]
				[ elen, off ] = vlq(event[2:])
				j += off
				print "elen = ", elen
				print "Comment", text[j:j+eln]
			
	
				i += elen

		else:
			print "Event: %02x" % ord(event_type)

			for n in range(length):
				print " %02x" % ord(text[i+n]),

			i += length

		print "\n-----"


		


if __name__ == "__main__":
	main()
