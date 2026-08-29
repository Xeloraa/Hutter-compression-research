#ifndef BTLSTM_H
#define BTLSTM_H
#include <valarray>
#include <vector>
#include <memory>
#include "lstm-layer-bd.h"

// cmix's Lstm with the 256-way softmax head replaced by a BINARY-TREE head.
// Adam, layer normalisation and exact BPTT (via LstmLayer) are untouched.
// Output cost per byte: 8*H instead of 256*H (~24x cheaper on that term).
class BtLstm {
 public:
  BtLstm(unsigned int input_size, unsigned int num_cells,
         unsigned int num_layers, int horizon, float learning_rate,
         float gradient_clip);
  void Perceive(unsigned int input);      // learn-from-last (BPTT) + advance
  float PBit(int c0) const;               // P(bit=1) at tree node c0 (1..255)
  void LearnBit(int c0, int bit, float p);// record error + update tree weights
 private:
  void Advance(unsigned int input);
  std::vector<std::unique_ptr<LstmLayer>> layers_;
  std::vector<unsigned int> input_history_;
  std::valarray<float> hidden_, hidden_error_;
  std::valarray<std::valarray<std::valarray<float>>> layer_input_;
  std::valarray<float> tree_w_;                      // 256 * hsize_
#ifdef TREE_ADAM
  std::valarray<float> tree_m_, tree_v_;
  float tree_t_;
#endif
  std::valarray<std::valarray<float>> bit_rows_;     // [horizon*8][hsize_]
  std::valarray<int> bit_node_;
  std::valarray<float> bit_err_;
  float learning_rate_;
  unsigned int num_cells_, epoch_, horizon_, input_size_, vocab_, hsize_;
  int cur_epoch_, bit_idx_;
};
#endif
