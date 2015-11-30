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

options.add_argument("--phonotactics", "-t", action="store_true",
	help="Read all the phonemes and create a phonotactics file.")

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
	sys.exit(0)


with open(args.input, "r") as f: data = json.load(f, object_pairs_hook=odict)
if args.chunker:
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

	# Calculate percentages
	for k, v in iteritems(clustersByOnset):
		clustersByOnset[k] = list(v)
	#endfor

	# Write out data
	with open(args.output, "w") as f: json.dump([clustersByOnset, clusters, envTotals, onsetTotals], f)
elif args.phonotactics:
	# Constraints, if needed: https://en.wikipedia.org/wiki/English_phonology#Phonotactics

	# grapheme: {("left"|"right"|"env"): { graph: total }, phoneme: {"total": #, ("left"|"right"|"env"): { graph: # } }
	# phoneme: {"total": #, ("left"|"right"|"env"): { phone: # } }
	g2p, pnn = {}, {}

	# Retrieve all possible graphemes.
	for v in itervalues(data):
		lenv = len(v)
		gp, stress, fv, lv = [], [], None, None
		for i, (g, p) in enumerate(v):
			if p[-1] in "012":
				p, s = p[:-1], p[-1]
				lv = i
				if fv is None: fv = i
			else: s = None
			gp.append((g, p))
			stress.append(s)
		#endfor
		for i, (g, p) in enumerate(gp):
			if g in g2p:
				tg = g2p[g]
				tg["total"] += 1
			else:
				tg = g2p[g] = {
					"total": 1,
					"left": {}, "right": {}, "env": {},
					"phones": {},
				}
			#endif

			if p in tg["phones"]:
				tgp = tg["phones"][p]
				tgp["total"] += 1
			else:
				tgp = tg["phones"][p] = {
					"total": 1,
					"left": {}, "right": {}, "env": {},
				}
			#endif

			prevG, prevP = v[i-1] if i > 0 else ("-", "-")
			nextG, nextP = v[i+1] if i + 1 < lenv else ("-", "-")
			envG, envP = prevG + "|" + nextG, prevP + "|" + nextP

			tg["left"][prevG] = tg["left"].get(prevG, 0) + 1
			tg["right"][nextG] = tg["right"].get(nextG, 0) + 1
			tg["env"][envG] = tg["env"].get(envG, 0) + 1

			tgp["left"][prevG] = tgp["left"].get(prevG, 0) + 1
			tgp["right"][nextG] = tgp["right"].get(nextG, 0) + 1
			tgp["env"][envG] = tgp["env"].get(envG, 0) + 1

			mul = 2 if i > fv and i < lv and stress[i] else 1
			if mul:
				if p in pnn:
					tp = pnn[p]
					tp["total"] += mul
				else:
					tp = pnn[p] = {
						"total": mul,
						"left": {}, "right": {}, "env": {},
					}
				#endif

				tp["left"][prevP] = tp["left"].get(prevP, 0) + mul
				tp["right"][nextP] = tp["right"].get(nextP, 0) + mul
				tp["env"][envP] = tp["env"].get(envP, 0) + mul
		#endfor
	#endfor

	# Write out data
	with open(args.output, "w") as f: json.dump([g2p, pnn], f)

	# stops = ["P", "B", "T", "D", "K", "G"]
	# affricates = ["CH", "JH"]
	# fricatives = ["F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"]
	# nasals = ["M", "N", "NG"]
	# liquids = ["L", "R"]
	# glides = ["Y", "W"] # also: semivowels
	# vowels = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW", "Y", "W"]

	# obstruents = stops + affricates + fricatives
	# approximates = liquids + glides
	# sonorants = nasals + approximates + vowels

	# voiced = ["B", "D", "G", "JH", "V", "DH", "Z", "ZH"] + sonorants

	# def l2r(l): return "(?:" + "|".join(l) + ")"

	# # Valid onset forms:
	# #  3C: S ([M T P K] Y | [T P K] R | [P K] L | K W | F R)
	# #  2C: obstruent approximate | S [P T K M N F TH]
	# #  1C: !NG
	# onset = re.compile(
	# 	"(?:S/(?:[MTPK]/Y|[TPK]/R|[PK]/L|K/W|F/R|[PTKMNF]|TH)"
	# 	"|" + l2r(obstruents) + "/" + l2r(approximates) +
	# 	"|(?!NG)[^/]+)$"
	# )

	# def findOnset(v, i):
	# 	st = max(0, i - 3)
	# 	vt = v[st : i]
	# 	pj = "/".join([ph for sp, ph in vt])
	# 	mo = onset.search(pj)
	# 	if mo:
	# 		idx = len(filter(lambda x: x, pj[0 : max(0, mo.start() - 1)].split("/")))
	# 		# Also return if this is a shakey syllabification
	# 		st += idx - 1
	# 		return vt[idx:], st >= 0 and v[st][1] in vowels
	# 	else:
	# 		return [], False
	# 	#endif
	# #enddef

	# # Maybe: Valid coda forms?

	# g2p, phonemes = {}, {}

	# for v in itervalues(data):
	# 	lenv = len(v)

	# 	nextOnset, nextHalf = None, None
	# 	gp, stress = [], []
	# 	for g, p in v:
	# 		if p[-1] in "012": p, s = p[:-1], p[-1]
	# 		else: s = None
	# 		gp.append((g, p))
	# 		stress.append(s)
	# 	#endfor

	# 	for i, (g, p) in enumerate(gp):
	# 		# We want a sort of syllable identity. This is: [onset] nucleus [coda] or C*VC*
	# 		# If only one is dropped from a syllable, it's more likely to be the coda that is.
	# 		left, right, silentE = [], [], None
	# 		if p in vowels:
	# 			# Find consonants to the left (onset)
	# 			if nextOnset:
	# 				left, half = nextOnset, nextHalf
	# 				nextOnset = None
	# 			else: left, half = findOnset(v, i)

	# 			# Find all consonants to the right (coda)
	# 			foundVowel = False
	# 			for j in range(i + 1, lenv):
	# 				# Find the next vowel
	# 				if v[j][:-1] in vowels:
	# 					# and its onset
	# 					nextOnset, nextHalf = findOnset(v, j)
	# 					# then between i and this is the coda
	# 					right = v[i+1:j-len(nextOnset)]
	# 					foundVowel = True
	# 					break
	# 				#endif
	# 			#endfor
	# 			if not foundVowel:
	# 				# Grab everything to the end, then
	# 				right = v[i+1:]
	# 			#endif

	# 			value1 = 0.5 if half else 1
	# 			value0 = 0.5 if half else 0

	# 			# Store information about each part of the syllable
	# 			for lg, lp in left:
	# 				if lp not in phonemes:
	# 					phonemes[lp] = {
	# 						"onsetInit": 0, "onsetMedial": 0, "onsetFinal": 0, "onsetSimple": 0,
	# 						"codaInit": 0, "codaMedial": 0, "codaFinal": 0, "codaSimple": 0,
	# 						"onsets": {}, "codas": {}, "envs": {},
	# 					}
	# 				#endif

	# 				# Add possible phonemes per grapheme
	# 				if lg not in g2p: g2p[lg] = {}
	# 				if lp in g2p[lg]:
	# 					g2p[lg][lp][0] += value1
	# 					g2p[lg][lp][2] += value0
	# 				else: g2p[lg][lp] = [value1, 0, value0]
	# 			#endfor

	# 			# Nucleus
	# 			cpj = "/".join([rp for rg, rp in right])
	# 			if p not in phonemes: phonemes[p] = { "onsets": {}, "codas": {}, "envs": {} }
	# 			phonemes[p]["codas"][cpj] = phonemes[p]["codas"].get(cpj, 0) + 1

	# 			value2 = 1. / (len(left) + 1)

	# 			def onen(ph):
	# 				opj = "/".join([lp for lg, lp in ph])
	# 				phonemes[p]["onsets"][opj] = phonemes[p]["onsets"].get(opj, 0) + value2
	# 				env = opj + "|" + cpj
	# 				phonemes[p]["envs"][env] = phonemes[p]["envs"].get(env, 0) + value2
	# 			#enddef

	# 			if half:
	# 				for i in range(len(left)): onen(left[i:])
	# 			else: onen(left)

	# 			if g not in g2p: g2p[g] = {}
	# 			if p in g2p[g]: g2p[g][p][1] += 1
	# 			else: g2p[g][p] = [0, 1, 0]

	# 			for rg, rp in right:
	# 				if rp not in phonemes:
	# 					phonemes[rp] = {
	# 						"onsetInit": 0, "onsetMedial": 0, "onsetFinal": 0, "onsetSimple": 0,
	# 						"codaInit": 0, "codaMedial": 0, "codaFinal": 0, "codaSimple": 0,
	# 						"onsets": {}, "codas": {}, "envs": {},
	# 					}
	# 				#endif

	# 				# Add possible phonemes per grapheme
	# 				if rg not in g2p: g2p[rg] = {}
	# 				if rp in g2p[rg]:
	# 					g2p[rg][rp][0] += value0
	# 					g2p[rg][rp][2] += value1
	# 				else: g2p[rg][rp] = [value0, 0, value1]
	# 			#endfor

	# 			def onco(side, ph, value):
	# 				lenl = len(ph)
	# 				if lenl == 1:
	# 					phonemes[ph[0][1]][side + "Simple"] += value
	# 				elif lenl > 1:
	# 					opj = "/".join([lp for lg, lp in ph])
	# 					phonemes[ph[0][1]][side + "Init"] += value
	# 					phonemes[ph[-1][1]][side + "Final"] += value
	# 					for i, (lg, lp) in enumerate(ph):
	# 						if i and i < lenl: phonemes[lp][side + "Medial"] += value
	# 						if opj not in phonemes[lp][side + "s"]:
	# 							phonemes[lp][side + "s"][opj] = value
	# 						else: phonemes[lp][side + "s"][opj] += value
	# 					#endfor
	# 				#endif
	# 			#enddef

	# 			if half:
	# 				for i in range(len(left) + 1):
	# 					onco("coda", left[:i], value2)
	# 					onco("onset", left[i:], value2)
	# 				#endfor
	# 			else: onco("onset", left, 1)

	# 			onco("coda", right, 1)
	# 		#endif
	# 	#endfor
	# #endfor
	
	# Write out data
	#with open(args.output, "w") as f: json.dump([g2p, phonemes], f)
else:
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