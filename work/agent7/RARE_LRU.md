# lastCW LRU-index oracle (modified Idea 1)

gamma(file-gap) was killed. This recode uses LRU membership and cost 1+log2(|cache|), independent of file distance while the id remains in the cache.
Rare-only: admit ids whose causal count so far is <=5; graduate-and-evict when count exceeds 5.

dic_bytes=1814514 tokens=391028 vocab=44515 unigram_bits=4124227 (28.41% of DIC-file bits)

## All-id LRU vs unigram (min of unigram and 1+log2 K)
- all K=64 save=412480 (10.00% uni, 2.842% DIC-file) hits=108935 save>20=306880 save2-5=30663 far_rare_hits=4/11489
- all K=256 save=342898 (8.31% uni, 2.362% DIC-file) hits=116271 save>20=225115 save2-5=34196 far_rare_hits=596/11489
- all K=1024 save=218422 (5.30% uni, 1.505% DIC-file) hits=100260 save>20=107558 save2-5=34415 far_rare_hits=2146/11489
- all K=4096 save=107619 (2.61% uni, 0.741% DIC-file) hits=68180 save>20=22287 save2-5=29658 far_rare_hits=3939/11489
- all K=16384 save=58634 (1.42% uni, 0.404% DIC-file) hits=46044 save>20=5246 save2-5=30747 far_rare_hits=10656/11489
- all K=65536 save=57397 (1.39% uni, 0.395% DIC-file) hits=45724 save>20=5246 save2-5=30939 far_rare_hits=11489/11489

## Rare-only LRU (causal count <=5)
- rare K=256 save=120316 (2.92% uni, 0.829% DIC-file) hits=19905 save2-5=44125 save6-20=56114 save>20=20077 far_rare_hits=1873/11489
- rare K=1024 save=103859 (2.52% uni, 0.715% DIC-file) hits=25342 save2-5=40128 save6-20=48968 save>20=14763 far_rare_hits=3128/11489
- rare K=4096 save=82221 (1.99% uni, 0.566% DIC-file) hits=33236 save2-5=36590 save6-20=38813 save>20=6819 far_rare_hits=5754/11489
- rare K=16384 save=68550 (1.66% uni, 0.472% DIC-file) hits=41149 save2-5=37827 save6-20=26166 save>20=4557 far_rare_hits=11489/11489
- rare K=65536 save=68550 (1.66% uni, 0.472% DIC-file) hits=41149 save2-5=37827 save6-20=26166 save>20=4557 far_rare_hits=11489/11489

## Interpretation
If almost all LRU save is still cnt>20, membership recoding did not create a rare-identity expert.
Survive as a rare expert only if rare-only save on cnt2-5 is a non-rounding slice of DIC-file bits and far_rare_hits is not ~0.
Still vs a global unigram, not vs fxcm word hashes.
