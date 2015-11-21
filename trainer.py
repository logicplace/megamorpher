#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2015 Sapphire Becker (logicplace.com)
# MIT Licensed

import timbl, timblapi, argparse, sys, json
from future.utils import iteritems
from collections import OrderedDict as odict

parser = argparse.ArgumentParser()
parser.add_argument("--chunk", "-c", action="store_true", help="Only chunk graphemes")
parser.add_argument("training", help="Training file name")
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

if args.chunk:
	with open(args.training, "r") as f:
		gc, data, envs = tuple(json.load(f))
		success, fail, problematic, untested = 0, 0, 0, 0
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
						ret.append((g, float(pg + gn - pgn) / max(ps + sn - psn, 1)))
					#endif
				#endfor
				return ret
			#enddef

			# P(<a> | "au") = <a>.next[u] / (<a>.next[u] + <au>.total)
			# P(grapheme boundary between prev and graph) = sum([gg[x][1].get(prev, 0) for x in gc[graph[0]]])

			def fitness(clusters):
				# For now, try avg...
				return float(sum(list(zip(*clusters))[1])) / len(clusters)
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
							f = fitness(c)
							if f > mf: mf, mc = f, c
						#endfor
						return mc
					#endif
				#endfor
				return clusters
			#endfor
			bestClusters = fork()

			# Test or just print if there's no verification
			if rt:
				fit, goal = fitness(bestClusters), list(zip(*rt))[0]
				if "_" in goal:
					print("Problematic:")
					problematic += 1
					goal = [x  for x in goal if x != "_"]
				#endif

				if list(zip(*bestClusters))[0] == goal:
					print("OK:", t, fit)
					success += 1
				else:
					print("NG:", t, fit)
					print("Found:", bestClusters)
					print("Wanted:", goal)
					fail += 1
			else:
				print(t, bestClusters, fitness(bestClusters))
				untested += 1
			#endif
		#endfor
		print("%i success; %i fail; %i untested; %i problematic" % (success, fail, problematic, untested))
	#endwith

	sys.exit(0)
#endif

classifiers = []

# i, limit = 0, 100
trainOn = []
with open(args.training, "r") as f:
	for l in f:
		l = l.rstrip()
		if l:
			if l[0] != "#":
				split = l.split(" ")
				classes = []
				for x in trainOn: classes.append(split.pop(x))
				for i, c in enumerate(classifiers): c.append(split, classes[i])
			elif l[0:5] == "#!w= ":
				tmp = l[5:].split(" ")
				with open("weights.txt", "w") as wf:
					wf.write("# Fea.\tWeight")
					for i, w in enumerate(tmp):
						if w == "-": trainOn.append(i)
						else: wf.write("\n%i\t%f" % (i - len(trainOn) + 1, float(w)))
					#endfor
				trainOn = trainOn[::-1]
				classifiers = [timbl.TimblClassifier("g2p%s" % x, "-a 1 +D") for x in trainOn]
			# else:
			# 	i += 1
			# 	if i >= limit: break
			#endif
		#endif
	#endfor
#endwith

for c in classifiers:
	c.train()
	c.api.getWeights("weights.txt", timblapi.Weighting.GR)
#classifier.save()

# Test
with open(args.testing, "r") as f:
	for l in f:
		l = l.rstrip()
		if l and l[0] != "#":
			features, goals = l.split(" "), []
			for x in trainOn: goals.append(features.pop(x))
			for i, c in enumerate(classifiers):
				try: tmp = c.classify(features)
				except timbl.ClassifyException as err:
					tmp = err
					print(err)
					sys.exit(1)
				print("Classifying '%s', should be %s:" % (" ".join(features), goals[i]), tmp)
			#endfor
		#endif
	#endfor
#endwith