// Reversible OOV pointer on a DIC stream. Matches work/agent7/oov_ptr.py
// usage: oovptr e in out
//        oovptr d in out
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iterator>
#include <list>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

static const unsigned char MARK = 5;
static const unsigned char K_ESCAPE = 0x0C;
static const int MIN_LEN = 6;

static std::unordered_set<std::string> load_dic(const char* path) {
  FILE* f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "oovptr: cannot open dic %s\n", path);
    exit(1);
  }
  std::unordered_set<std::string> words;
  std::string buf;
  int c;
  while ((c = getc(f)) != EOF) {
    if (c >= 'a' && c <= 'z') buf.push_back((char)c);
    else if (!buf.empty()) {
      words.insert(buf);
      buf.clear();
    }
  }
  if (!buf.empty()) words.insert(buf);
  fclose(f);
  return words;
}

static int skip_code(const unsigned char* s, int i, int n) {
  unsigned char c = s[i];
  if (c == K_ESCAPE) return i + 2 > n ? n : i + 2;
  if (c >= 0x80) {
    i += 1;
    if (c > 0xCF && i < n) {
      unsigned char c2 = s[i];
      i += 1;
      if (c2 > 0xCF && i < n) i += 1;
    }
    return i;
  }
  return i + 1;
}

static void uleb_enc(std::vector<unsigned char>& out, unsigned n) {
  while (true) {
    unsigned char b = (unsigned char)(n & 0x7F);
    n >>= 7;
    if (n) out.push_back((unsigned char)(b | 0x80));
    else {
      out.push_back(b);
      return;
    }
  }
}

static unsigned uleb_dec(const unsigned char* s, int n, int* i) {
  unsigned v = 0, shift = 0;
  while (*i < n) {
    unsigned char b = s[(*i)++];
    v |= (unsigned)(b & 0x7F) << shift;
    if (b < 0x80) return v;
    shift += 7;
  }
  fprintf(stderr, "oovptr: truncated uleb\n");
  exit(1);
}

struct Lru {
  std::list<std::string> order;  // back = most recent
  std::unordered_map<std::string, std::list<std::string>::iterator> pos;
  int rank_of(const std::string& w) const {
    if (!pos.count(w)) return 0;
    int r = 0;
    for (auto jt = order.rbegin(); jt != order.rend(); ++jt) {
      ++r;
      if (*jt == w) return r;
    }
    return 0;
  }
  void touch(const std::string& w) {
    auto it = pos.find(w);
    if (it != pos.end()) {
      order.erase(it->second);
    }
    order.push_back(w);
    pos[w] = std::prev(order.end());
  }
  std::string at_rank(int rank) const {
    int r = 0;
    for (auto jt = order.rbegin(); jt != order.rend(); ++jt) {
      ++r;
      if (r == rank) return *jt;
    }
    fprintf(stderr, "oovptr: bad rank %d size %zu\n", rank, order.size());
    exit(1);
  }
};

static std::vector<unsigned char> read_all(const char* path) {
  FILE* f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "oovptr: cannot open %s\n", path);
    exit(1);
  }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::vector<unsigned char> v((size_t)n);
  if (n && fread(v.data(), 1, (size_t)n, f) != (size_t)n) {
    fprintf(stderr, "oovptr: short read\n");
    exit(1);
  }
  fclose(f);
  return v;
}

static void write_all(const char* path, const std::vector<unsigned char>& v) {
  FILE* f = fopen(path, "wb");
  if (!f) {
    fprintf(stderr, "oovptr: cannot write %s\n", path);
    exit(1);
  }
  if (!v.empty() && fwrite(v.data(), 1, v.size(), f) != v.size()) {
    fprintf(stderr, "oovptr: short write\n");
    exit(1);
  }
  fclose(f);
}

static std::vector<unsigned char> encode(const std::vector<unsigned char>& s,
                                          const std::unordered_set<std::string>& dic) {
  std::vector<unsigned char> out;
  out.reserve(s.size());
  Lru lru;
  int i = 0, n = (int)s.size();
  while (i < n) {
    unsigned char c = s[i];
    if (c >= 'a' && c <= 'z') {
      int j = i;
      while (j < n && s[j] >= 'a' && s[j] <= 'z') ++j;
      std::string w((const char*)s.data() + i, (size_t)(j - i));
      if (j - i >= MIN_LEN && !dic.count(w)) {
        int rank = lru.rank_of(w);
        if (rank > 0) {
          out.push_back(MARK);
          uleb_enc(out, (unsigned)rank);
          lru.touch(w);
          i = j;
          continue;
        }
        out.insert(out.end(), s.begin() + i, s.begin() + j);
        lru.touch(w);
        i = j;
        continue;
      }
      out.insert(out.end(), s.begin() + i, s.begin() + j);
      i = j;
      continue;
    }
    if (c == MARK) {
      out.push_back(MARK);
      out.push_back(0);
      ++i;
      continue;
    }
    if (c >= 0x80 || c == K_ESCAPE) {
      int j = skip_code(s.data(), i, n);
      out.insert(out.end(), s.begin() + i, s.begin() + j);
      i = j;
      continue;
    }
    out.push_back(c);
    ++i;
  }
  return out;
}

static std::vector<unsigned char> decode(const std::vector<unsigned char>& s,
                                          const std::unordered_set<std::string>& dic) {
  std::vector<unsigned char> out;
  out.reserve(s.size() * 2);
  Lru lru;
  int i = 0, n = (int)s.size();
  while (i < n) {
    unsigned char c = s[i];
    if (c == MARK) {
      if (i + 1 >= n) {
        fprintf(stderr, "oovptr: truncated MARK\n");
        exit(1);
      }
      if (s[i + 1] == 0) {
        out.push_back(MARK);
        i += 2;
        continue;
      }
      ++i;
      unsigned rank = uleb_dec(s.data(), n, &i);
      std::string w = lru.at_rank((int)rank);
      out.insert(out.end(), w.begin(), w.end());
      lru.touch(w);
      continue;
    }
    if (c >= 'a' && c <= 'z') {
      int j = i;
      while (j < n && s[j] >= 'a' && s[j] <= 'z') ++j;
      std::string w((const char*)s.data() + i, (size_t)(j - i));
      out.insert(out.end(), s.begin() + i, s.begin() + j);
      if (j - i >= MIN_LEN && !dic.count(w)) lru.touch(w);
      i = j;
      continue;
    }
    if (c >= 0x80 || c == K_ESCAPE) {
      int j = skip_code(s.data(), i, n);
      out.insert(out.end(), s.begin() + i, s.begin() + j);
      i = j;
      continue;
    }
    out.push_back(c);
    ++i;
  }
  return out;
}

int main(int argc, char** argv) {
  if (argc < 4 || (argv[1][0] != 'e' && argv[1][0] != 'd')) {
    fprintf(stderr, "usage: oovptr e in out\n       oovptr d in out\n");
    fprintf(stderr, "english.dic must be in CWD or set OOVPTR_DIC\n");
    return 1;
  }
  const char* dic_path = getenv("OOVPTR_DIC");
  if (!dic_path) dic_path = "english.dic";
  auto dic = load_dic(dic_path);
  auto in = read_all(argv[2]);
  std::vector<unsigned char> out =
      argv[1][0] == 'e' ? encode(in, dic) : decode(in, dic);
  write_all(argv[3], out);
  fprintf(stderr, "oovptr %c %zu -> %zu\n", argv[1][0], in.size(), out.size());
  return 0;
}
