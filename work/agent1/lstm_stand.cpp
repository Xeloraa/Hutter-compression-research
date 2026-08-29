// Standalone tree-head LSTM entropy probe.
// Reports cross-entropy bpb and us/byte. Not a real-pipeline result.
#include "btl-bd.h"
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <cmath>
#include <vector>

extern float g_initMul;
extern int g_blocks;
extern float g_forgetBias;

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr,
      "usage: lstm_stand in.bin [bytes] [cells] [layers] [blocks] "
      "[initMul] [forgetBias] [lr] [horizon]\n");
    return 1;
  }
  FILE* f = fopen(argv[1], "rb");
  if (!f) { perror(argv[1]); return 1; }
  fseek(f, 0, SEEK_END);
  long flen = ftell(f);
  fseek(f, 0, SEEK_SET);
  int nbytes = (argc > 2) ? atoi(argv[2]) : (int)flen;
  if (nbytes <= 0 || nbytes > flen) nbytes = (int)flen;
  int cells = (argc > 3) ? atoi(argv[3]) : 72;
  int layers = (argc > 4) ? atoi(argv[4]) : 3;
  g_blocks = (argc > 5) ? atoi(argv[5]) : 4;
  g_initMul = (argc > 6) ? (float)atof(argv[6]) : 0.5f;
  g_forgetBias = (argc > 7) ? (float)atof(argv[7]) : 1.0f;
  float lr = (argc > 8) ? (float)atof(argv[8]) : 0.03f;
  int horizon = (argc > 9) ? atoi(argv[9]) : 50;

  std::vector<unsigned char> buf(nbytes);
  if ((int)fread(buf.data(), 1, nbytes, f) != nbytes) { perror("read"); return 1; }
  fclose(f);

  srand(0);
  BtLstm lstm(256, cells, layers, horizon, lr, 10);
  lstm.Perceive(0);

  double bits = 0;
  clock_t t0 = clock();
  for (int i = 0; i < nbytes; ++i) {
    unsigned c = buf[i];
    int c0 = 1;
    for (int k = 7; k >= 0; --k) {
      int bit = (c >> k) & 1;
      float p = lstm.PBit(c0);
      if (p < 1e-6f) p = 1e-6f;
      if (p > 1.f - 1e-6f) p = 1.f - 1e-6f;
      bits += bit ? -log2((double)p) : -log2(1.0 - (double)p);
      lstm.LearnBit(c0, bit, p);
      c0 = (c0 << 1) | bit;
    }
    lstm.Perceive(c);
  }
  double sec = double(clock() - t0) / CLOCKS_PER_SEC;
  double bpb = bits / nbytes;
  double us = (sec * 1e6) / nbytes;
  printf("file=%s n=%d cells=%d layers=%d blocks=%d initMul=%.3f forgetBias=%.3f lr=%.4f horizon=%d  bpb=%.4f us/byte=%.1f sec=%.2f bits=%.0f\n",
         argv[1], nbytes, cells, layers, g_blocks, g_initMul, g_forgetBias, lr, horizon, bpb, us, sec, bits);
  return 0;
}
