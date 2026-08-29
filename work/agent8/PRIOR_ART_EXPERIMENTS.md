# Prior art → experiments on THIS stack

Official record: fx2-cmix **110,793,128**. cmix-lex ~109.19M uses fxcm_v26 + cmix stack + shipped article order + lex tail. We are fxcm26+LSTM only.

## Already in fxcm26 (do not reimplement)

- Reverse dictionary + stemmer word types + four word streams
- Match model expectedByte as CM context (`smA`)
- Mixer 8 = `deccode` / lastCW

## Missing vs fx2-cmix (highest EV)

fx2-cmix `fxcmv1.cpp` (after LSTM is wired from cmix):

```
extern int lstmpr, lstmex;
mxA[9].cxt = (bpos<<8)*4 + (fails&3)*256 + lstmex;
mxInputs1.add(stretch(lstmpr));
mxInputs2.add(stretch(lstmpr)/2);
```

cmix `ByteModel::ex` = argmax of the LSTM softmax over the remaining byte range.
Our tree head’s MAP byte is the greedy walk (`BtLstm::ExpectedByte`).

**We only have stretch(bp) on L1 slots 544/545.** Missing:

| id | replica | cost | file |
|---|---|---|---|
| E35 | `mxInputs2.n[17] = stretch(bp)/2` | 0 (pad already allocated, N=32) | `fxcm26_slots.cpp` `-DLSTM_L2_INPUT=1` |
| E36a | `mxA1[1].cxt = ExpectedByte` (M=256) | ~16 KB mixer weights | `-DLSTM_MEX_CXT=1` |
| E36b | fx2 formula `bpos*1024+(fails&3)*256+lstmex` | ~512 KB | `-DLSTM_MEX_CXT=2` |

Do **not** overwrite our `mxA[9]` (lastWT + stream3bR) — fx2 has a different mixer map. Use the unused L2 mixer `mxA1[1]` (currently M=1, cxt stuck at 0).

## Not free (paid permutation)

voyage-large-2-instruct → t-SNE article order is **shipped**. Not E10. Only retry if compressed permutation + gain beats 517,996.

## Do not run 3 MB until E30d/e finish
