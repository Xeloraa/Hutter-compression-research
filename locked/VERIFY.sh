#!/bin/bash
# Full byte-exact verification: enwik -> DIC -> cmp -> cmp^-1 -> DIC^-1 -> enwik
# usage: ./VERIFY.sh <enwik-slice>
set -e
cd "$(dirname "$0")"
IN="$1"; N=$(stat -c%s "$IN"); W=$PWD
T=$(mktemp -d)
cd dic
"$W/dicprep" e english.dic "$IN" "$T/x.dic"
cd "$W"
s=$(date +%s); ./cmp c "$T/x.dic" "$T/x.arc"; e=$(date +%s); CT=$((e-s))
s=$(date +%s); ./cmp d "$T/x.arc" "$T/x.back"; e=$(date +%s); DT=$((e-s))
cmp "$T/x.dic" "$T/x.back" || { echo "CODEC ROUNDTRIP FAIL"; exit 1; }
cd dic; "$W/dicprep" d english.dic "$T/x.back" "$T/out" "$N"; cd "$W"
if cmp -s "$IN" "$T/out"; then V=EXACT; else V=FAIL; fi
A=$(stat -c%s "$T/x.arc")
echo "input=$N archive=$A bpb=$(python3 -c "print(f'{$A*8/$N:.4f}')") ctime=${CT}s dtime=${DT}s FULL_PIPELINE=$V"
rm -rf "$T"
