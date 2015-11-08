Implementation Model
====================
Stages:
 * Grapheme - Phoneme Association
 * G2P Feature Analysis
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

# Run G2P Association
TODO

# Run G2P Feature Analysis
TODO

# Run Morphological Analysis
TODO