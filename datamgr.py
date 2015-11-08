#!/usr/bin/env python
#-*- coding:utf-8 -*-

import re, json, argparse, sys
from future.utils import iteritems
from collections import OrderedDict as odict

parser = argparse.ArgumentParser()
options = parser.add_mutually_exclusive_group()

options.add_argument("--generalize", "-G", action="store_true",
	help="Generalize the given assoc output file.")

makeset = parser.add_argument_group()
makeset.add_argument("--graphemic-context", "-g", default=0,
	help="Use a graphemic context of the given number on each side. 1 = one grapheme on each side.")
makeset.add_argument("--phonetic-context", "-p", default=0,
	help="Use a phonemic context of the given number on each side. 1 = one phoneme on each side.")
makeset.add_argument("--stress", "-s", action="store_true",
	help="Separate stress from phoneme on vowels (and put - for consonants).")
makeset.add_argument("--silent-e", "-e", action="store_true",
	help="Determine whether or not the word has a silent e on the end and store that information.\n"
	"This may be inaccurate for compound words.")
makeset.add_argument("--vowel-index", "-v", action="store_true",
	help="When it's a vowel, notate which vowel it is (0 = first, etc).")

parser.add_argument("input", help="Input file name")
parser.add_argument("output", help="Output file name")

args = parser.parse_args(sys.argv[1:])

noSilentE = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "EY", "IH", "IY", "OW", "OY", "UH", "UW", "Y", "W"]

if args.generalize:
	spelling = re.compile(r'# Graphemes from "([^"]+)"')
	entry = re.compile(r'[^ ]+ [^ ]+ ([^ ]+) [^ ]+ [^ ]+ (.+)')

	out, cur = odict(), None
	with open(args.input, "r") as f:
		for line in f:
			if line[0] == "#":
				cur = spelling.match(line).group(1).lower()
				out[cur] = []
			elif line.rstrip():
				out[cur].append(list(entry.match(line).groups()))
			#endif
		#endfor
	#endwith

	with open(args.output, "w") as f:
		f.write("{ ")
		iterator = iteritems(out)
		k, v = iterator.next()
		f.write('"%s": %s' % (k, json.dumps(v)))
		for k,v in iterator:
			f.write(',\n"%s": %s' % (k, json.dumps(v)))
		#endfor
		f.write(" }\n")
	#endwith
else:
	with open(args.input, "r") as f: data = json.load(f, object_pairs_hook=odict)

	with open(args.output, "w") as f:
		gc, pc = int(args.graphemic_context), int(args.phonetic_context)
		stress, vi, se = args.stress, args.vowel_index, args.silent_e

		weights, names = [1], ["graph"]

		if gc:
			names += ["g-%i" % i for i in range(gc, 0, -1)] + ["g+%i" % i for i in range(gc)]
			# Graphemic weights taken from research by Daelemans et al., 2005, p. 65
			# Daelemans, W., & Van den Bosch, A. (2005). Memory-based language processing. Cambridge University Press.
			gc3, outer = min(gc, 3), max(gc - 3, 0)
			weights += (
				[0.01] * outer +
				[0.06, 0.09, 0.24, 0.29, 0.12, 0.06][3-gc3:3-gc3+gc3*2] +
				[0.01] * outer
			)
		if pc:
			# TODO: add real weights
			names += ["p-%i" % i for i in range(gc, 0, -1)] + ["p+%i" % i for i in range(gc)]
			weights += [0.10] * (pc * 2)
		if vi:
			# TODO: add real weight
			names.append("silent-e")
			weights.append(0.2)
		if se:
			# TODO: add real weight
			names.append("silent-e")
			weights.append(0.2)
		if stress:
			names.append("stress")
			weights.append("-")
		#endif

		names.append("phone")
		weights.append("-")

		f.write("#!n= " + " ".join(names) + "\n")
		f.write("#!w= " + " ".join(map(str, weights)) + "\n\n")

		def fetchWithPadding(v, i, c, g):
			lenv = len(v)
			tmp = (
				# Left padding, if any
				["-"] * max(c - i, 0) +
				# Surrounding graphemes
				[(x if g else y) for x,y in v[max(i - c, 0) : min(i + c + 1, lenv)]] +
				# Right padding, if any
				["-"] * max(i + c + 1 - lenv, 0)
			)
			# Remove grapheme in question
			tmp.pop(gc)
			return tmp
		#enddef

		vowel = re.compile(r'^([A-Z]+)([0-2])$')
		for k, v in iteritems(data):
			f.write('# Featuresets for word "%s"\n' % k)

			silents = ["-"] * len(v)
			if se:
				# Check for silent Es and where
				for i, (g, p) in enumerate(v):
					vm = vowel.match(p)
					if vm: p = vm.group(1)
					if p not in noSilentE and g[-1] == "e":
						for j in range(i + 1): silents[j] = "e"
					#endif
				#endfor
			#endif

			for i, (g, p) in enumerate(v):
				features = [g]
				if gc: features += fetchWithPadding(v, i, gc, True)
				if pc: features += fetchWithPadding(v, i, pc, False)
				if se: features.append(silents[i])
				if stress:
					vm = vowel.match(p)
					if vm:
						p, s = vm.groups()
						features.append(s)
					else: features.append("-")
				#endif

				f.write(" ".join(features) + " %s\n" % p)
			#endfor

			f.write("\n")
		#endfor
	#endwith
#endif