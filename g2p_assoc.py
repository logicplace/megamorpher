#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2015 Sapphire Becker (logicplace.com)
# MIT Licensed

import re

# These are more or less listed in probability order.
p2g = {
	# Stops
	"B": ["b", "bb", "be", "bbe"],
	"D": ["d", "dd", "ed", "de"],
	"G": ["g", "gh", "gg", "x", "gue"],
	"K": ["ck", "kh", "k", "kk", "ke", "cc", "c", "ch", "qu", "que", "q", "che", "cq", "ca", "x", "kc", "g"],
	"P": ["p", "pe", "pp"],
	"T": ["t", "tt", "dt", "ed", "tte", "te", "z", "d"],
	# Affricates
	"CH": ["tch", "tsch", "tsh", "ch", "che", "cz", "ti", "t", "cc", "ci", "c"],
	"JH": ["dge", "dg", "dj", "j", "ge", "gi", "g", "d"],
	# Fricatives (+ Aspirates)
	"SH": ["sh", "ti", "ci", "ssi", "si", "sch", "c", "ch", "she", "ss", "zs"],
	"DH": ["th"],
	"F": ["ff", "f", "gh", "ph", "fh", "fe", "w"],
	"HH": ["ch", "h"],
	"S": ["ss", "s", "sse", "se", "ce", "z", "sc", "cc", "c", "sce", "sw"],
	"TH": ["th", "the"],
	"V": ["v", "ve", "w"],
	"Z": ["zz", "z", "ss", "s", "ze", "se", "si", "sth"],
	"ZH": ["z", "si", "s", "ge"],
	# Nasals
	"M": ["mm", "m", "me", "mb", "nm", "mn"],
	"N": ["kn", "nn", "ne", "nne", "n", "gn", "nh"],
	"NG": ["ng", "nx", "n", "nge"],
	# Glides (Liquids + Semivowels)
	"L": ["ll", "l", "lle", "le", "lh"],
	"R": ["rr", "r", "re", "rp", "wr"],
	"W": ["wh", "w", "u", "o"],
	"Y": ["y", "i", "j", "ll", "l", "e", ""],
	# Vowels
	"AA": ["augh", "ough", "aa", "ah", "a", "aah", "ho", "o", "ow", "au", "ahh", "al", "as"],
	"AE": ["a", "ae", "an"],
	"AH": ["a", "u", "e", "o", "ou", "aa", "ah", "i", "y", "ae", "ui", "ue", "oh", "ia", ""],
	"AO": ["o", "au", "a", "oa", "ou", "u", "augh", "al"],
	"AW": ["au", "ow", "ou", "aue"],
	"AY": ["i", "igh", "ie", "y", "ai", "aj", "ay", "ayy", "ei", "ae", "hei"],
	"EH": ["a", "e", "aa", "ai", "ea", "ae", "eh", "ue", "ei", "u"],
	"ER": ["er", "or", "orr", "ar", "ir", "err", "ur", "eur", "re", "ure", "our", "r", "aer", "ear", "u", "her", "ere", "arr", "ahr", "urr", "irr"],
	"EY": ["eigh", "a", "e", "ey", "ai", "ae", "ay", "ei", "ais", "ej", "ue", "et"],
	"IH": ["i", "e", "y", "ie", "ea", "a", "u", "ui", "iu", "ae", "o", "hy"],
	"IY": ["y", "iy", "iyy", "ey", "ee", "i", "ie", "ei", "e", "ae", "ea", "ye", "oe", "ui", "ii"],
	"OW": ["ough", "o", "ow", "oa", "oe", "au", "os", "eaux", "ault", "ou", "aud"],
	"OY": ["oy", "oi"],
	"UH": ["u", "oo", "ou", "ueh"],
	"UW": ["ou", "u", "oo", "uw", "eu", "ue", "ieu", "o", "ew"],
}

nrovowel = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "EY", "IH", "IY", "OW", "OY", "UH", "UW", "Y", "W"]
vowel = nrovowel + ["ER"]
vowels = re.compile(r'^[aeiouyw]+$')

def g2p_assoc(spelling, phonemes):
	"""
	Takes a given spelling and a given set of phonemes and
	returns the most likely split of graphemes that would
	map to those phonemes.
	"""
	global p2g

	# Possible phonemes are listed in the .phones files in cmudict.
	# What associations this uses are in the p2g dict above.

	# Vowels may be listed with stress but for this we don't need
	# stress information, so just remove it.
	rmStress = re.compile(r'^([A-Z]+)[0-9]*$')
	# We can more or less safely assume that the RE matches.
	phonemes = [rmStress.match(p).group(1) for p in phonemes]

	# Create a initial setup that is likely inaccurate.
	# The system will then try to shift values around to find the most
	# accurate variation.
	assoc, vcount = [0], 0
	for i in range(1, len(phonemes)):
		p = phonemes[i]

		# Vowel spelling rules are extremely complex.
		# Let the genetics iron them out.
		if p in vowel:
			vcount += 1
			continue
		#endif

		# Find the nearest match.
		mins = len(spelling)
		for x in p2g[p]:
			s = spelling.find(x, assoc[-1] + 1)
			if s != -1: mins = min(mins, s)
		#endfor
		if mins == len(spelling): mins = assoc[-1] + vcount
		assoc.append(mins)

		# Reset vcount since this was a consonant.
		vcount = 0
	#endif

	assoc = list(range(len(phonemes)))

	def byFitness(x): return -x.fitness()

	def generate(world):
		# We should find something in that time yeah?
		for x in range(13):
			newWorld = world[:]
			for x in world:
				if x.fitness() == 1: return x
				else:
					newWorld.extend(x.parthenogenesis())
				#endif
			#endfor
			# TODO: Working around some weirdo sorting bug.
			world = sorted(newWorld, key=byFitness)[:30]
		#endfor

		# Oh well?
		return world[0]
	#enddef

	spellingLow = spelling.lower()
	best = generate([Attempt(spellingLow, assoc, phonemes)])
	graphemes = best.graphemes()
	if best.fitness() < 0.96:
		print('"%s" best guess (%i%%):\n %s\n %s\n %s' % (
			spelling, best.fitness() * 100,
			", ".join(["%4s" % x for x in phonemes]),
			", ".join(["%4s" % x for x in graphemes]),
			", ".join(["%3i%%" % (fit * 100) for fit in best.graphemeFits])
		))
		add = True
		while True:
			changes = input("Changes?: ")
			if changes:
				if changes[0] == "!":
					add = False
					changes = changes[1:]
				elif changes[0] == "?":
					return None
				#endif
				if changes:
					graphemes = [x.strip() for x in changes.split(",")]
			#endif

			if "".join(graphemes) != spellingLow or len(graphemes) != len(phonemes):
				print("error in input")
			else: break
		#endwhile

		# Add new graphemes
		if add:
			for i, p in enumerate(phonemes):
				g = graphemes[i]
				if g not in p2g[p]: p2g[p].append(g)
			#endfor
		#endif
	#endif

	return graphemes
#enddef

class Attempt:
	"""
	An attempt at matching up a phoneme list into a spelling.
	"""

	def __init__(self, spelling, assoc, phonemes):
		self.spelling, self.assoc, self.phonemes = spelling, assoc, phonemes

		# assoc and phonemes are expected to be the same length
		self.splen = len(spelling)
		self.end = len(phonemes) - 1

		# fitness value is cacheable
		self.fitnessValue = None
		self.graphemeFits = [] 
	#enddef

	def graphemes(self):
		prev, ret = 0, []
		for x in self.assoc[1:]:
			ret.append(self.spelling[prev:x])
			prev = x
		#endfor
		ret.append(self.spelling[prev:])
		return ret
	#enddef

	def fitness(self):
		"""
		Caclulate fitness of attempt.
		ie. how well the phonemes match up to the spelling
		"""
		# Return cached value if it exists
		if self.fitnessValue is not None: return self.fitnessValue

		# Otherwise calculate it
		fitness = 0
		for i, p in enumerate(self.phonemes):
			s, e = self.assoc[i], self.assoc[i+1] if i < self.end else None
			ok = self.spelling[s:e] in p2g[p]
			gfit = 0
			if p in vowel:
				if ok: gfit += 6

				# Check for vowels on the left and right.
				# If there is a lefthand vowel and vowel letter(s) for it
				# or if there is no lefthand vowels and no excess vowel letter(s).
				if i == 0 or s <= 0 or (
					(self.phonemes[i-1] in nrovowel) == (bool(vowels.match(self.spelling[s-1])) or
						(self.assoc[i-1] == self.assoc[i] and "" in p2g[self.phonemes[i-1]]))
				): gfit += 2

				# Same for the right side.
				if i == self.end or e >= self.splen or (
					(self.phonemes[i+1] in vowel) == (bool(vowels.match(self.spelling[e])) or
						(self.assoc[i+1] == (self.assoc[i+2] if i < self.end -1 else self.splen) and "" in p2g[self.phonemes[i+1]]))
				): gfit += 2

				# If there are consonants not explicitely part of the value, try to subtract 1.
				if not ok and not vowels.match(self.spelling[s:s+1]):
					gfit = max(0, gfit - 1)
				#endif
			elif ok: gfit += 10
			else:
				# Check without ending.
				tmpSpelling = self.spelling[s:]
				for x in p2g[p]:
					if tmpSpelling.startswith(x):
						gfit = 5
						break
					#endif
				#endfor
			#endif

			# Being non-empty (unless empty is allowed) is preferred.
			if s == e or (e is None and s == self.splen):
				# If it's <K>x</K><S/>, <G>x</G><Z/>, <NG>nx</NG><Z/>, ...
				if (i > 0 and (self.phonemes[i-1], p, self.spelling[self.assoc[i-1]:s])
					in [("K","S","x"), ("G","Z","x"), ("NG","Z","nx"), ("NG","K","nx")]
					# ...or <Y/><Vowel>u</Vowel>, ignore.
					or i < self.end and p == "Y" and self.phonemes[i+1] in vowel
					and self.spelling[e:(self.assoc[i+2] if i < self.end - 1 else None)] == "u"
				):
					gfit = 10
				# Even if it's allowed, it's not necessarily optimal.
				elif ok: gfit -= 1
				else: gfit = 0
			else: gfit = max(gfit, 1)

			# We want this to be within 0 to 1.
			self.graphemeFits.append(gfit / 10.)
			fitness += gfit
		#endfor
		# We want this to be within 0 to 1.
		self.fitnessValue = fitness / float(10 * len(self.phonemes))

		return self.fitnessValue
	#enddef

	def parthenogenesis(self):
		"""
		Create new versions by offsetting each.
		"""
		newv = []

		# Ensure this was run.
		self.fitness()

		# This creates the new attempt.
		def create(newv, i, direction, cascade=False):
			assoc = self.assoc[:]
			assoc[i] += direction
			# Make sure that i is not at an end.
			if i > 0 and i <= self.end and assoc[i] > 0 and assoc[i] <= self.splen:
				# If it collides with its preceeding association...
				if assoc[i] < assoc[i-1]:
					if cascade:
						# ...we should shift everything but only if cascade is on.
						j = i
						while j > 0 and assoc[j] < assoc[j-1]:
							assoc[j-1] = assoc[j]
							j -= 1
						#endwhile
					#endif

				# If it's the same as its following association...
				elif i < self.end and assoc[i] > assoc[i+1]:
					if cascade:
						# ...we should shift everything but only if cascade is on.
						diff = assoc[i] - assoc[i+1] + 1
						for j in range(i+1, self.end + 1):
							if i == self.end: print(assoc[j], "+", diff)
							assoc[j] += diff
						if assoc[-1] >= self.splen: return
					else: return
				#endif

				# Return the new attempt.
				#if i == self.end: print("Trying end as: %i" % assoc[-1], "bc", direction)
				newv.append(Attempt(self.spelling, assoc, self.phonemes))
			#endif
		#enddef

		offs = 0
		for i, x in enumerate(self.graphemeFits):
			if i != 0 and x < 1:
				offs += 1
				for l in set(map(len, p2g[self.phonemes[i]])):
					create(newv, i, -l, True)
				#endfor
				if i <= self.end:
					if offs > 1: create(newv, i, +1, True)
					create(newv, i, offs, True)
				#endif
			elif x == 1:
				if offs:
					create(newv, i, -1, True)
					create(newv, i, +1, True)
				#endif
				offs = 0
			#endif
		#endfor

		return newv
	#enddef
#endclass

if __name__ == "__main__":
	import sys

	nonword, invalid, alternate = re.compile("^[^A-Z]"), re.compile("[\-0-9'._]"), re.compile("^(.+)(\([0-9]*\))?$")
	print("If you're asked for changes, hit enter to accept or enter the graphemes in csv. By default the changes will add new phoneme-grapheme associations, to stop this, prefix your entry with !")

	contFrom = None

	if len(sys.argv) >= 3:
		if sys.argv[1] == "-c": contFrom = sys.argv[2]
	#endif

	out = open("training.txt", "a" if contFrom else "w")
	with open("cmudict/cmudict-0.7b", "r") as f:
		lineNum = 0
		for line in f:
			if nonword.match(line): continue

			line = line.rstrip()
			spelling, pronunciation = line.split("  ")

			# Remove any alternate pronunciation designations.
			spelling = alternate.match(spelling).group(1)
			if contFrom:
				if spelling == contFrom: contFrom = None
				continue
			#endif

			# For now, ignore certain complex strings.
			if invalid.search(spelling): continue

			phonemes = pronunciation.split(" ")

			# Also seems complex...
			if len(phonemes) > len(spelling) + spelling.count("U"): continue

			print(spelling, ":", ", ".join(phonemes))
			assoc = g2p_assoc(spelling, phonemes)
			if assoc:
				graphemes = ["-", "-"] + assoc + ["-", "-"]
				# Training format is essentially grapheme in question in the middle
				# with surrounding graphemes for context, followed by phoneme, finally.
				# Like: X-2 X-1 X X+1 X+2 PHONE

				out.write('# Graphemes from "%s"\n' % spelling)
				for i in range(2, len(graphemes) - 2):
					out.write(" ".join([x if x else "_" for x in graphemes[i-2:i+3]] + [phonemes[i-2]]) + "\n")
				#endfor
				out.write("\n")

				#if lineNum == 10: break
				lineNum	+= 1
			#endif
		#endfor
	#endwith
	out.close()
#endif