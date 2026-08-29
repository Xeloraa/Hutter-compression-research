#include "btl-bd.h"
#include <cmath>
#include <algorithm>

static inline float sig(float x){
  if(x>30.f) return 1.f; if(x<-30.f) return 0.f;
  return 1.f/(1.f+expf(-x));
}

BtLstm::BtLstm(unsigned int input_size, unsigned int num_cells,
    unsigned int num_layers, int horizon, float learning_rate,
    float gradient_clip) : input_history_(horizon),
    hidden_(num_cells * num_layers + 1), hidden_error_(num_cells),
    layer_input_(std::valarray<std::valarray<float>>(std::valarray<float>
    (1 + num_cells * 2), num_layers), horizon),
    learning_rate_(learning_rate), num_cells_(num_cells), epoch_(0),
    horizon_(horizon), input_size_(0), vocab_(input_size),
    hsize_(num_cells * num_layers + 1), cur_epoch_(0), bit_idx_(0) {
  hidden_[hidden_.size() - 1] = 1;
  for (int epoch = 0; epoch < horizon; ++epoch) {
    layer_input_[epoch][0].resize(1 + num_cells);
    for (unsigned int i = 0; i < num_layers; ++i) {
      layer_input_[epoch][i][layer_input_[epoch][i].size() - 1] = 1;
    }
  }
  for (unsigned int i = 0; i < num_layers; ++i) {
    layers_.push_back(std::unique_ptr<LstmLayer>(new LstmLayer(
        layer_input_[0][i].size() + vocab_, 0, vocab_,
        num_cells, horizon, gradient_clip, learning_rate)));
  }
  tree_w_.resize(256 * hsize_, 0.0f);                       // p = sigmoid(0) = 0.5
  bit_rows_.resize(horizon * 8, std::valarray<float>(hsize_));
  bit_node_.resize(horizon * 8, 0);
  bit_err_.resize(horizon * 8, 0.0f);
}

float BtLstm::PBit(int c0) const {
  const float* w = &tree_w_[(size_t)c0 * hsize_];
  float z = 0;
  for (unsigned int j = 0; j < hsize_; ++j) z += w[j] * hidden_[j];
  return sig(z);
}

void BtLstm::LearnBit(int c0, int bit, float p) {
  const float d = p - (float)bit;
  const int slot = cur_epoch_ * 8 + (bit_idx_ & 7);
  bit_node_[slot] = c0;
  bit_err_[slot] = d;
  float* w = &tree_w_[(size_t)c0 * hsize_];
  std::valarray<float>& row = bit_rows_[slot];
  const float g = learning_rate_ * d;
  for (unsigned int j = 0; j < hsize_; ++j) { row[j] = w[j]; w[j] -= g * hidden_[j]; }
  ++bit_idx_;
}

void BtLstm::Advance(unsigned int input) {
  for (unsigned int i = 0; i < layers_.size(); ++i) {
    auto start = begin(hidden_) + i * num_cells_;
    std::copy(start, start + num_cells_, begin(layer_input_[epoch_][i]) + input_size_);
    layers_[i]->ForwardPass(layer_input_[epoch_][i], input, &hidden_, i * num_cells_);
    if (i < layers_.size() - 1) {
      auto start2 = begin(layer_input_[epoch_][i + 1]) + num_cells_ + input_size_;
      std::copy(start, start + num_cells_, start2);
    }
  }
  cur_epoch_ = epoch_;
  bit_idx_ = 0;
  ++epoch_;
  if (epoch_ == horizon_) epoch_ = 0;
}

void BtLstm::Perceive(unsigned int input) {
  int last_epoch = epoch_ - 1;
  if (last_epoch == -1) last_epoch = horizon_ - 1;
  int old_input = input_history_[last_epoch];
  input_history_[last_epoch] = input;
  if (epoch_ == 0) {
    for (int epoch = horizon_ - 1; epoch >= 0; --epoch) {
      for (int layer = layers_.size() - 1; layer >= 0; --layer) {
        int offset = layer * num_cells_;
        // tree head: 8 nodes per step instead of 256 outputs
        for (int k = 0; k < 8; ++k) {
          const int slot = epoch * 8 + k;
          const float error = bit_err_[slot];
          const std::valarray<float>& row = bit_rows_[slot];
          for (unsigned int j = 0; j < hidden_error_.size(); ++j) {
            hidden_error_[j] += row[j + offset] * error;
          }
        }
        int prev_epoch = epoch - 1;
        if (prev_epoch == -1) prev_epoch = horizon_ - 1;
        int input_symbol = input_history_[prev_epoch];
        if (epoch == 0) input_symbol = old_input;
        layers_[layer]->BackwardPass(layer_input_[epoch][layer], epoch, layer,
            input_symbol, &hidden_error_);
      }
    }
  }
  Advance(input);
}
