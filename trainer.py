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
		if args.testing[-5:] == ".json": test = json.load(f)
		else: test = f.read().splitlines()
	#endwith
#endif

vowels = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"]

classifier = None
if args.morph:
	# i, limit = 0, 100
	trainOn = []
	doWeights = False
	classifier = timbl.TimblClassifier("morpher", "-a 1 +D")
	with open(args.morphs, "r") as f:
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
gsuccess, gfail, problematic, untested = 0, 0, 0, 0
psuccess, pfail, pbadg = 0, 0, 0
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

		for i, o in enumerate(opts):
			# Take top for these.
			if i <= fv or o[0][0] not in vowels or i >= lv: res.append(o[0])

			# Middle vowels have trouble, do by phonemic environment
			else: res.append(ptprob(i, opts[i-1][0][0], opts[i+1][0][0]))
		#endfor

		return [x for x, y in res], fitness(res)

		# # Permutate options
		# sureness = [(None, 0)] * 2
		# cnt = 0
		# dopts = dict(enumerate(opts))
		# mp = []
		# for i, v in enumerate(opts):
		# 	# Find most probable given neighbor's options
		# 	lside = [x for x, _ in dopts.get(i - 1, [("-", 1)])]
		# 	rside = [x for x, _ in dopts.get(i + 1, [("-", 1)])]

		# 	winners = {}
		# 	for l, r in itertools.product(lside, rside):
		# 		ttl = ptotal(i, l, r)
		# 		mph, mpr = None, 0
		# 		if ttl:
		# 			for ph, _ in v:
		# 				pr = pprob(l, ph, r, ttl)
		# 				if pr > mpr: mph, mpr = ph, pr
		# 			#endfor

		# 		if mph is not None: winners[mph] = winners.get(mph, 0) + 1
		# 	#endfor

		# 	if len(winners) == 0: print(v)

		# 	print(winners)
		# 	winner = max(winners.items(), key=lambda x: x[1])[0]
		# 	for ph, pr in v:
		# 		if ph == winner:
		# 			mp.append((ph, pr, winners[ph] / sum(winners.values())))
		# 			break
		# #endfor
		# mf = phitness(mp)

		# while True:
		# 	unbroken = True
		# 	#print("Idxs(%i)[%i]" % (cnt, len(idxs)), end=": ")
		# 	for i, x in enumerate(idxs):
		# 		idxs[i] = (x + 1) % len(opts[i])
		# 		#print("%i +[%i] 1 = %i" % (x, len(opts[i]), idxs[i]), end=", ")
		# 		if idxs[i] != 0:
		# 			unbroken = False
		# 			break
		# 		#endif
		# 	#endfor
		# 	if unbroken: break

		# 	#print("")

		# 	cnt += 1

		# 	probs = [v[idxs[i]] for i, v in enumerate(opts)]
		# 	dprobs = dict(enumerate(probs))

		# 	phpr = []
		# 	for i, (ph, pr) in enumerate(probs):
		# 		(l, lp), (r, rp) = dprobs.get(i - 1, ("-", 1)), dprobs.get(i + 1, ("-", 1))

		# 		phpr.append(pprob(l, ph, r, ptotal(i, l, r)))
		# 	#endfor

		# 	probs = [(a, b, phpr[i]) for i, (a, b) in enumerate(probs)]
		# 	probfit = phitness(probs)

		# 	if probfit > sureness[-1][1]:
		# 		sureness.pop(0)
		# 		sureness.append((probs, probfit))
		# 		print("\nNew best: ", probs, probfit)
		# 	#endif
		# #endwhile

		# # Returns (most probable, surity, [other options])
		# mp, mf = sureness.pop()
		# return mp, mf, list(reversed(sureness))
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
		if "_" in goal:
			print("Problematic:")
			problematic += 1
			goal = [x  for x in goal if x != "_"]
		#endif

		if [g for g, prb in bestClusters] == ggoal:
			gsuccess += 1

			pmp, pmf, opts = phitest(bestClusters)
			if [p for p, pg, pp in pmp] == pgoal:
				print("OK:", t, fit)
				psuccess += 1
			else:
				print("Phones NG:", t, pmf)
				pfail += 1
			#endif
		else:
			print("Chunks NG:", t, fit)
			print("Found:", bestClusters)
			print("Wanted:", goal)
			gfail += 1
			pbadg += 1
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
				while True:
					cmd = classifier.classify((["-", "-"] + phones)[-3:])
					if cmd == "<":
						# Remove
						if not args.simple: print("Popping", graphs[-1], phones[-1])
						phones.pop()
					elif cmd == ".":
						# Stop
						if not args.simple: print("Stopping, morphing")
						rmSilentE(graphs)
						break
					else:
						# Append
						g, p = cmd.split("/")
						if not args.simple: print("Appending", g, p)
						rmSilentE(graphs)
						graphs.append(g)
						phones.append(p)
					#endif
				#endwhile
			except timbl.ClassifyException as err:
				print("WARNING: Failled classification at a point, assuming end.")
			#endtry
			graphs += ["i", "te"]
			phones += ["AY", "T"]
			print("".join(graphs))
		elif args.simple: print(list(zip(graphs, phones)))
		untested += 1
	#endif
#endfor
if not args.simple:
	print("Entries: %i problematic; %i untested" % (problematic, untested))
	print("Chunks: %i success; %i fail" % (gsuccess, gfail))
	print("Phones: %i success; %i fail (+%i bad chunking)" % (psuccess, pfail, pbadg))


if not args.morph: sys.exit(0)


# # Test
# with open(args.testing, "r") as f:
# 	for l in f:
# 		l = l.rstrip()
# 		if l and l[0] != "#":
# 			features, goals = l.split(" "), []
# 			for x in trainOn: goals.append(features.pop(x))
# 			for i, c in enumerate(classifiers):
# 				try: tmp = c.classify(features)
# 				except timbl.ClassifyException as err:
# 					tmp = err
# 					print(err)
# 					sys.exit(1)
# 				print("Classifying '%s', should be %s:" % (" ".join(features), goals[i]), tmp)
# 			#endfor
# 		#endif
# 	#endfor
# #endwith