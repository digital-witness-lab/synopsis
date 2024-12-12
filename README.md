# synopsis
Semantic trend inference with secure multi-party computation. This research prototype code accompanies the draft manuscript ''Synopsis: Secure and private trend inference from encrypted semantic embeddings.''

_Overview_:

Synopsis is implemented in MP-SPDZ,<sup>1</sup> a popular MPC library. This research prototype includes the following: 

- **run.py**: a sample Python script that performs dimension reduction and optional Gaussian noise injection for coarse-grained query types
- **synopsis.mpc**: a sample MP-SPDZ script that accepts client queries and performs all other secure querying functions
- **out.json**: semantic embedding vectors. _n.b._: Pending approval of data release for the dataset used in our paper analysis, this is a corpus of embeddings extracted from the Microsoft Speech Corpus's Gujarati dataset. Again, this is public data<sup>2</sup> and is _not_ the original source data used in our Ram Temple investigation. 

Pending dockerification, this should run out-of-the-box. 



<sup>1</sup> <url>https://eprint.iacr.org/2020/521</url>

<sup>2</sup> <url>https://www.microsoft.com/en-us/download/details.aspx?id=105292</url>


## Running


### Docker setup

CONFIG.mine:
```
CXX = clang++-11
USE_NTL = 0
MY_CFLAGS += -I/usr/local/include -DINSECURE
MY_LDLIBS += -Wl,-rpath -Wl,/usr/local/lib -L/usr/local/lib
PREP_DIR = '-DPREP_DIR="Player-Data/"'
SSL_DIR = '-DSSL_DIR="Player-Data/"'
MOD = -DGFP_MOD_SZ=2
```

- GENERAL SETUP:
    - base mpspdz:mascot-party
    - make -j mascot-party.x
    - make -j setup
    - make -j Fake-Offline.x
    - ./Scripts/setup-online.sh
    - ./Fake-Offline.x 2
    - pip install scikit-learn

- PROGRAM DEPENDENT:
    - ./compile.py -l synopsis
    - ./Scripts/mascot.sh -F synopsis  # this runs the thing


### Host Setup

- Start with `data.jsonl` with newline separated json records with "text" and "embedding" records. "embedding" is a list of floats
- Run `run.py` with `data.jsonl` substituted in line 35
    - this outputs `benchmarks.tsv` which is nice for checking results
    - outputs `query.tsv` and `database.tsv` for use with SPDZ
        - could instead output each file into single line, space separated 32bit fixed floats
- Manually create single-line 32bit fixed floats
    - `database.tsv` file should map to `Player-Data/Input-P0-0`
    - `database.tsv` file is squared element-wise and mapped to `Player-Data/Input-P1-0`
    - `query.tsv` is hardcoded currently in `synopsis.mpc` (line 338)
- Run program dependent parts from up top
- Look at stdout for results
