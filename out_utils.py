"""
Various output utilities...
"""

class Debug():
	def __init__(self):
		self.debug_level = 0	

	def out(self, level, *args):
		if level >= self.debug_level:
			print args

