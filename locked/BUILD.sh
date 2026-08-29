#!/bin/bash
# Build the locked candidate. Produces ./dic (preprocessor) and ./cmp (compressor).
set -e
cd "$(dirname "$0")"
g++ -O2 -std=c++11 -o dicprep dic/main.cpp dic/dictionary.cpp
g++ -O3 -march=native -ffast-math -DUNIX -fno-strict-aliasing -std=c++11 \
    -o cmp src/fxcm26_bd92.cpp src/btl-bd.cpp src/lstm-layer-bd.cpp src/sigmoid.cpp -lm
test -f english.dic || cp dic/english.dic ./english.dic
echo "built: ./dicprep ./cmp  (english.dic must be in CWD when running ./cmp)"
