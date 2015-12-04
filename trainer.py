#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2015 Sapphire Becker (logicplace.com)
# MIT Licensed

import timbl, timblapi
import argparse, sys, json
from future.utils import iteritems
from collections import OrderedDict as odict
import itertools

parser = argparse.ArgumentParser()
parser.add_argument("--simple", "-s", action="store_true", help="Simple output")
parser.add_argument("--morph", "-m", default=None, help="Morpheme training file")
parser.add_argument("--chunking", "-c", help="Chunking file")
parser.add_argument("--phonotactics", "-p", "-t", help="Phonotactics file")
testing = parser.add_mutually_exclusive_group()
testing.add_argument("-w", "--word", default=None, help="Test a word passed on the command line")
testing.add_argument("testing", nargs="?", help="Testing file name")
args = parser.parse_args(sys.argv[1:])

if args.word: test = { args.word: [] }
else:
	with open(args.testing, "r") as f:
		if args.testing[-5:] == ".json": test = json.load(f, object_pairs_hook=odict)
		else: test = f.read().splitlines()
	#endwith
#endif

vowels = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"]

classifier = None
if args.morph:
	# i, limit = 0, 100
	trainOn = []
	doWeights = False
	classifier = timbl.TimblClassifier("morpher", "-a 1 +D" + (" +v+s" if args.simple else ""))
	with open(args.morph, "r") as f:
		for l in f:
			l = l.rstrip()
			if l:
				if l[0] != "#":
					split = l.split(" ")
					klass = split.pop()
					classifier.append(split, klass)
				# else:
				# 	i += 1
				# 	if i >= limit: break
				#endif
			#endif
		#endfor
	#endwith

	classifier.train()
#endif

with open(args.chunking, "r") as f: gc, data, envs, ons = json.load(f)
with open(args.phonotactics, "r") as f2: g2p, pnn = json.load(f2)
problematic, untested = 0, 0
gsuccess, gfail, gosuccess, gofail = 0, 0, 0, 0
psuccess, pfail, posuccess, pofail = 0, 0, 0, 0
for t, rt in iteritems(test):
	stest = "-" + t + "-"
	dtest = dict(enumerate(stest))
	ltest = len(stest)

	def fetchPotential(i):
		ret = []
		for j in range(i + 1, ltest + 1):
			g = stest[i:j]
			if g in data:
				p, n = dtest.get(i - 1, "-"), dtest.get(j, "-")

				pg, gn, pgn = data[g][1].get(p, 0), data[g][2].get(n, 0), data[g][3].get(p+n, 0)
				ps, sn, psn = envs.get(p+g, 0), envs.get(g+n, 0), envs.get(p+g+n, 0)

				#gOfOns, totalOns = data[g][0], ons[g[0]] 
				ret.append((g, float(pg + gn - pgn) / max(ps + sn - psn, 1)))
			#endif
		#endfor
		return ret
	#enddef

	# P(<a> | "au") = <a>.next[u] / (<a>.next[u] + <au>.total)
	# P(grapheme boundary between prev and graph) = sum([gg[x][1].get(prev, 0) for x in gc[graph[0]]])

	def phitness(phones):
		# Format: [(phone, P(// | left is <> u right is <>), P(// | left is // u right is //)), ...]
		return float(sum([pg * pp for p, pg, pp in phones])) / len(phones)
	#enddef

	def phitest(clusters):
		idxs = [0] * len(clusters)
		opts = [list(g2p[g]["phones"].keys()) for g, _ in clusters]
		dc = dict([(i, g) for i, (g, _) in enumerate(clusters)])

		def gprob(x, i):
			g = dc[i]

			l, r = dc.get(i - 1, "-"), dc.get(i + 1, "-")

			plg, prg, peg = g2p[g]["phones"][x]["left"].get(l, 0), g2p[g]["phones"][x]["right"].get(r, 0), g2p[g]["phones"][x]["env"].get(l + "|" + r, 0)
			glg, grg, geg = g2p[g]["left"].get(l, 0), g2p[g]["right"].get(r, 0), g2p[g]["env"].get(l + "|" + r, 0)

			return float(plg + prg - peg) / max(glg + grg - geg, 1)
		#enddef

		for i, o in enumerate(opts):
			# Phoneme options for each chunk, sorted by probability given chunk environment.
			opts[i] = sorted([(k, gprob(k, i)) for k in o], key = lambda x: -x[1])
		#endfor

		def ptotal(i, l, r):
			# Calculate total for this option set based on options for this index
			tlp, trp, tep = 0, 0, 0
			for tph, tpr in opts[i]:
				tlp += pnn[tph]["left"].get(l, 0)
				trp += pnn[tph]["right"].get(r, 0)
				tep += pnn[tph]["env"].get(l + "|" + r, 0)
			#endfor

			return tlp + trp - tep
		#enddef

		def pprob(l, ph, r, ttl):
			plp, prp, pep = pnn[ph]["left"].get(l, 0), pnn[ph]["right"].get(r, 0), pnn[ph]["env"].get(l + "|" + r, 0)

			tmp = float(plp + prp - pep)
			if tmp == ttl == 0: return 0
			elif ttl == 0: raise Exception("BAD TOTAL ERROR: top was %i" % tmp)
			else: return tmp / ttl
		#enddef

		def ptprob(i, l, r):
			mp, mf = None, 0
			ttl = ptotal(i, l, r)
			for ph, pr in opts[i]:
				tf = pprob(l, ph, r, ttl)
				#print(ph, pr, tf)
				tf *= pr
				if tf > mf: mp, mf = ph, tf
			#endfor
			return mp, mf
		#enddef

		# Find and fuzz middle vowels because fml
		res, fv, lv = [], None, None
		for i, o in enumerate(opts):
			if o[0][0] in vowels:
				lv = i
				if fv is None: fv = i

		if fv is None: fv = lv = 0

		for i, o in enumerate(opts):
			# Take top for these.
			if i <= fv or o[0][0] not in vowels or i >= lv: res.append(o[0])

			# Middle vowels have trouble, do by phonemic environment
			else: res.append(ptprob(i, opts[i-1][0][0], opts[i+1][0][0]))
		#endfor

		return [x for x, y in res], fitness(res)
	#enddef

	def fitness(clusters):
		return float(sum([p for g, p in clusters])) / max(len(clusters), 1)
	#enddef

	def fork(clusters = [], start = 1):
		for i in range(start, ltest - 1):
			p = fetchPotential(i)
			lp = len(p)

			if lp == 0:
				# ...?
				print("Non-cluster...")
			elif lp == 1:
				# Only one option, can assume it's right.
				clusters.append(p[0])
			else:
				# Fork each option and find the fittest.
				mf, mc = 0, None
				for j in p:
					c = fork(clusters[:] + [j], i + len(j[0]))
					f = 0 if phitest(c)[0].count(None) != 0 else fitness(c)
					if f > mf: mf, mc = f, c
				#endfor
				if mc is not None: return mc
			#endif
		#endfor
		return clusters
	#endfor
	bestClusters = fork()

	# Test or just print if there's no verification
	if rt:
		fit, (ggoal, pgoal) = fitness(bestClusters), list(zip(*rt))
		if "_" in ggoal:
			print("Problematic:")
			problematic += 1
			ggoal = [x for x in ggoal if x != "_"]
		#endif

		# Remove stress
		pgoal = [x[:-1] if x[-1] in "012" else x for x in pgoal]

		bcb = [g for g, prb in bestClusters]
		if bcb == list(ggoal):
			print("Chunks OK:", t, fit)
			gosuccess += 1
			gsuccess += len(bcb)

			pmp, pmf = phitest(bestClusters)
		else:
			print("Chunks NG:", t, fit)
			print(" Found:", bestClusters)
			print(" Wanted:", ggoal)
			gofail += 1

			for x, y in zip(bcb, ggoal):
				if x == y: gsuccess += 1
				else: gfail += 1
			#endfor

			pmp, pmf = phitest(list(zip(ggoal, [1] * len(ggoal))))
		#endif
		
		if pmp == pgoal:
		#if [p for p, pg, pp in pmp] == pgoal:
			print("Phones OK:", t, fit)
			posuccess += 1
			psuccess += len(pmp)
		else:
			print("Phones NG:", t, pmf)
			print(" Found:", pmp)
			print(" Wanted:", pgoal)
			pofail += 1

			for x, y in zip(pmp, pgoal):
				if x == y: psuccess += 1
				else: pfail += 1
			#endfor
		#endif
	else:
		graphs, phones = [x for x,y in bestClusters], phitest(bestClusters)[0]

		if not args.simple: print(t, bestClusters, fitness(bestClusters), phitest(bestClusters))

		if args.morph:
			def rmSilentE(gg):
				if gg[-1][-1] == "e" and len(gg[-1]) > 1:
					gg[-1] = gg[-1][:-1]
			#enddef

			# Keep going til we stop.
			try:
				ms = 0
				while True:
					cmd, opts, surity = classifier.classify((["-", "-"] + phones)[-3:])
					ms += 1
					pfx = "Morph step %i (%s, %.2f%%):" % (ms, opts, surity * 100)
					if cmd == "<":
						# Remove
						if not args.simple: print(pfx, "Popping", graphs[-1], phones[-1])
						graphs.pop()
						phones.pop()
					elif cmd == ".":
						# Stop
						if not args.simple: print(pfx, "Stopping, morphing")
						rmSilentE(graphs)
						break
					else:
						# Append
						g, p = cmd.split("/")
						if not args.simple: print(pfx, "Appending", g, p)
						rmSilentE(graphs)
						graphs.append(g)
						phones.append(p)
					#endif
				#endwhile
			except timbl.ClassifyException as err:
				print("WARNING: Failled classification at step %i, assuming end." % ms)
			#endtry
			graphs += ["i", "te"]
			phones += ["AY", "T"]
			print("".join(graphs))
		elif args.simple: print(list(zip(graphs, phones)))
		untested += 1
	#endif
#endfor
if not args.simple and not args.word:
	print("Entries: %i problematic; %i untested" % (problematic, untested))
	print("Chunks: %i chunk success; %i chunk fail; %i word success; %i word fail" % (
		gsuccess, gfail, gosuccess, gofail))
	print("Phones: %i phone success; %i phone fail; %i word success; %i word fail" % (
		psuccess, pfail, posuccess, pofail))
