#!/usr/bin/env python
#-*- coding:utf-8 -*-

import re, json, argparse, sys
from future.utils import iteritems, iterkeys, itervalues
from collections import OrderedDict as odict

parser = argparse.ArgumentParser()
options = parser.add_mutually_exclusive_group()

options.add_argument("--generalize", "-G", action="store_true",
	help="Generalize the given assoc output file.")

options.add_argument("--chunker", "-c", action="store_true",
	help="Read all the graphemes and create a chunking file.")

makeset = options.add_argument_group()
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
makeset.add_argument("--truth", "-1", action="store_true",
	help="Don't output a phoneme, just output a 1.")

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
elif args.chunker:
	with open(args.input, "r") as f: data = json.load(f, object_pairs_hook=odict)

	# onset: [grapheme, ...]
	clustersByOnset = {}
	onsetTotals, envTotals = {}, {}

	# grapheme: [count of occurrences, count of non-occurrences despite avaiable letters]
	clusters = {}

	# Retrieve all possible graphemes.
	for v in itervalues(data):
		lenv = len(v)
		for i, (g, p) in enumerate(v):
			if g[0] in clustersByOnset:
				clustersByOnset[g[0]].add(g)
				onsetTotals[g[0]] += 1
			else:
				clustersByOnset[g[0]] = set([g])
				onsetTotals[g[0]] = 1
			#endif

			preceding = v[i-1][0][-1] if i > 0 else "-"
			following = v[i+1][0][0] if i + 1 < lenv else "-"
			environment = preceding + following
			if g in clusters:
				clusters[g][0] += 1
				pset, fset, eset = clusters[g][1], clusters[g][2], clusters[g][3]
				pset[preceding] = pset.get(preceding, 0) + 1
				fset[following] = fset.get(following, 0) + 1
				eset[environment] = eset.get(environment, 0) + 1
			else: clusters[g] = [1, {preceding: 1}, {following: 1}, {environment: 1}] #, {}, 0
			envTotals[preceding + g] = 0
			envTotals[g + following] = 0
			envTotals[preceding + g + following] = 0
		#endfor
	#endfor

	for k in iterkeys(data):
		k = "-" + k + "-"
		unzips = [k[i:] for i in range(len(k))]
		# Grab all i-character sequences in this string.
		for i in range(2, len(unzips)):
			for chunk in map(''.join, zip(*unzips[:i])):
				if chunk in envTotals: envTotals[chunk] += 1
			#endfor
		#endfor
	#endfor

	# Review them to find non-occurrences
	# for k, v in iteritems(data):
	# 	# Count how often this could have been a different cluster with the same onset.
	# 	for i, (g, p) in enumerate(v):
	# 		onset, probs = g[0], clusters[g][3]
	# 		s = "".join([x for x, y in v[i:]])
	# 		for x in clustersByOnset[onset]:
	# 			if x != g and s.startswith(x):
	# 				probs[x] = probs.get(x, 0) + 1
	# 			#endif
	# 		#endfor
	# 	#endfor

	# 	# Count numbers of spellings.
	# 	lenk = len(k)
	# 	for i in range(lenk):
	# 		for j in range(i + 1, lenk + 1):
	# 			bit = k[i:j]
	# 			if bit in clusters: clusters[bit][4] += 1
	# 		#endfor
	# 	#endfor
	# #endfor

	# def scount(sp, envTotals=envTotals):
	# 	if sp not in envTotals:
	# 		envTotals[sp] = sum([x.count(sp) for x in iterkeys(data)])
	# 	return envTotals[sp]
	# #enddef

	# Calculate percentages
	for k, v in iteritems(clustersByOnset):
		total = float(onsetTotals[k])
		v = clustersByOnset[k] = list(v)
		# for g in v:
		# 	#occured = clusters[g][0]
		# 	clusters[g][0] /= total

		# 	context = clusters[g][1]
		# 	for p, x in iteritems(context):
		# 		try: context[p] /= float(scount(p + g))
		# 		except ZeroDivisionError: context[p] = 0
		# 	#endfor
		# 	context = clusters[g][2]
		# 	for n, x in iteritems(context):
		# 		try: context[n] /= float(scount(g + n))
		# 		except ZeroDivisionError: context[n] = 0
		# 	#endfor
		# 	context = clusters[g][3]
		# 	for e, x in iteritems(context):
		# 		try: context[e] /= float(scount(e[0] + g + e[1]))
		# 		except ZeroDivisionError: context[e] = 0
		# 	#endfor
		# #endfor
	#endfor

	# Write out data
	with open(args.output, "w") as f: json.dump([clustersByOnset, clusters, envTotals], f)
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
			names.append("vowel-index")
			weights.append(0.8)
		if se:
			# TODO: add real weight
			names.append("silent-e")
			weights.append(0.2)
		if stress:
			names.append("stress")
			weights.append("-")
		#endif

		names.append("true" if args.truth else "phone")
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

			vowelIndex = 0
			for i, (g, p) in enumerate(v):
				features, vm = [g], None
				if vi or stress: vm = vowel.match(p)

				if gc: features += fetchWithPadding(v, i, gc, True)
				if pc: features += fetchWithPadding(v, i, pc, False)
				if vi:
					if vm:
						features.append(str(vowelIndex))
						vowelIndex += 1
					else: features.append("-")
				#endif
				if se: features.append(silents[i])
				if stress:
					if vm:
						p, s = vm.groups()
						features.append(s)
					else: features.append("-")
				#endif

				f.write(" ".join(features) + " %s\n" % (1 if args.truth else p))
			#endfor

			f.write("\n")
		#endfor
	#endwith
#endif