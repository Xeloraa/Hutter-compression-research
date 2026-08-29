#include "dictionary.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv) {
  if (argc < 5 || (argv[1][0] != 'e' && argv[1][0] != 'd')) {
    fprintf(stderr, "usage: dicprep e dic in out\n");
    fprintf(stderr, "       dicprep d dic in out orig_len\n");
    return 1;
  }
  FILE* dicf = fopen(argv[2], "rb");
  FILE* in = fopen(argv[3], "rb");
  FILE* out = fopen(argv[4], "wb");
  if (!dicf || !in || !out) {
    fprintf(stderr, "dicprep: open failed\n");
    return 1;
  }
  if (argv[1][0] == 'e') {
    fseek(in, 0, SEEK_END);
    long len = ftell(in);
    fseek(in, 0, SEEK_SET);
    preprocessor::Dictionary dict(dicf, true, false);
    dict.Encode(in, (int)len, out);
  } else {
    if (argc < 6) {
      fprintf(stderr, "dicprep d requires orig_len\n");
      return 1;
    }
    int n = atoi(argv[5]);
    preprocessor::Dictionary dict(dicf, false, true);
    for (int i = 0; i < n; ++i) putc(dict.Decode(in), out);
  }
  fclose(dicf);
  fclose(in);
  fclose(out);
  return 0;
}
