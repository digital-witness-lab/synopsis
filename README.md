# synopsis
Semantic trend inference with secure multi-party computation. This research prototype code accompanies the draft manuscript ''Synopsis: Secure and private trend inference from encrypted semantic embeddings.''

_Overview_:

Synopsis is implemented in MP-SPDZ,<sup>1</sup> a popular MPC library. This research prototype includes the following: 

- **run.py**: a sample Python script that performs dimension reduction and optional Gaussian noise injection for coarse-grained query types
- **synopsis.mpc**: a sample MP-SPDZ script that accepts client queries and performs all other secure querying functions
- **out.json**: semantic embedding vectors. _n.b._: Pending approval of data release for the dataset used in our paper analysis, this is a corpus of embeddings extracted from the Microsoft Speech Corpus's Gujarati dataset. Again, this is public data<sup>2</sup> and is _not_ the original source data used in our Ram Temple investigation. 

Pending dockerification, this should run out-of-the-box. 



<sup>1</sup> https://eprint.iacr.org/2020/521

<sup>2</sup> https://www.microsoft.com/en-us/download/details.aspx?id=105292
