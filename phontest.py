import phonetics, json

f = open("stones.json")
stones = json.load(f)
f.close()

pc = open("phon-change.json", "w")
pn = open("phon-nochange.json", "w")
pc.write("{\n")
pn.write("{\n")
for x, v in sorted(stones.items()):
	x, v = str(x), str(v)
	s = v[0:-3]
	f = pn if x == s else pc
	f.write('\t"%s": ["%s",\n' % (x, v))
	for x in [
		(phonetics.soundex(x), phonetics.caverphone(x), phonetics.metaphone(x), phonetics.nysiis(x)),
		(phonetics.soundex(s), phonetics.caverphone(s), phonetics.metaphone(s), phonetics.nysiis(s)),
		(phonetics.soundex(v), phonetics.caverphone(v), phonetics.metaphone(v), phonetics.nysiis(v))
	]:
		f.write('\t\t["%s", "%s", "%-10s", "%-15s"],\n' % x)
	#endfor
	f.write('\t],\n')
#endfor
pc.write("}")
pn.write("}")
pc.close()
pn.close()