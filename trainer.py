#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2015 Sapphire Becker (logicplace.com)
# MIT Licensed

import timbl, argparse, sys

classifiers = []

parser = argparse.ArgumentParser()
parser.add_argument("training", help="Training file name")
parser.add_argument("testing", help="Testing file name")
args = parser.parse_args(sys.argv[1:])

# i, limit = 0, 100
weights, trainOn = [], []
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
				for i, w in enumerate(tmp):
					if w == "-": trainOn.append(i)
					else: weights.append(float(w))
				#endfor
				trainOn = trainOn[::-1]
				classifiers = [timbl.TimblClassifier("g2p%s" % x, "-a 1 +D -W weights%s" % x) for x in trainOn]
			# else:
			# 	i += 1
			# 	if i >= limit: break
			#endif
		#endif
	#endfor
#endwith

for c in classifiers: c.train()
#classifier.save()

# Test
with open(args.testing, "r") as f:
	for l in f:
		l = l.rstrip()
		if l and l[0] != "#":
			features, goals = l.split(" "), []
			for x in trainOn: goals.append(features.pop(x))
			for i, c in enumerate(classifiers):
				print("Classifying '%s', should be %s:" % (
					" ".join(features), goals[i]), c.classify(features)
				)
			#endfor
		#endif
	#endfor
#endwith