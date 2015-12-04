Implementation Model
====================
Stages:
 * Grapheme - Phoneme Association
 * Grapheme & Phoneme Corpus Analysis
 * Spelling to Phonemes
 * Phoneme-based Morpho-Derivational Steps Analysis

Grapheme - Phoneme Association
------------------------------


Instructions for Ubuntu
=======================
From this directory, whose path must have no spaces:

# Setup and installation
sudo apt-get install libboost-python1.54-dev libtar-dev libbz2-dev libxml2-dev

wget http://software.ticc.uvt.nl/timbl-latest.tar.gz
wget http://software.ticc.uvt.nl/ticcutils-latest.tar.gz

tar -xvf ticcutils-latest.tar.gz
cd ticcutils-*
./bootstrap.sh
./configure
make
sudo make install
cd ..

tar -xvf timbl-latest.tar.gz
cd timbl-*
./configure
make
sudo make install
cd ..

git clone https://github.com/proycon/python-timbl
cd python-timbl
sudo python3 setup3.py build_ext --timbl-include-dir=/usr/local/include/timbl --timbl-library-dir=/usr/local/lib --boost-library-dir=/usr/lib/x86_64-linux-gnu install
# Note you may have to adjust the boost lib location. This worked for me on x64.

svn checkout http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/

# A fullset.json is already included, so you can skip the g2p_assoc.py and generalization.

# Run G2P Association:
# This will automatically overwrite training.txt if you have one already.
./g2p_assoc.py

# You can continue (aka start) from a word with:
# This will append to the existing training.txt
./g2p_assoc.py -c WORD

# You need to generalize it now because this was written for an old dumb idea and I didn't want to retrofit it:
./datamgr.py -G training.txt fullset.json

# Create a training set and a testing set:
# Note that there is already a testingset.json provided with some pokemon names
# this will be overwritten by using this command!
./datamgr.py -S 2000 -C trainingset.json fullset.json testingset.json

# Run G/P Corpus Analysis:
./datamgr.py -c trainingset.json traingraphs.json
./datamgr.py -t trainingset.json trainphones.json

# Apply suffix to a word with full output:
./trainer.py -c traingraphs.json -t trainphones.json -m stones.txt -w WORD

# Just output derivation:
./trainer.py -c traingraphs.json -t trainphones.json -m stones.txt -sw WORD

# Run over testset for testing chunking and phonemization:
./trainer.py -c traingraphs.json -t trainphones.json testingset.json > results.txt
