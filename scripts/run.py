from sklearn.random_projection import johnson_lindenstrauss_min_dim, GaussianRandomProjection
from sklearn import random_projection
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from scipy import stats
from scipy.spatial import distance
import numpy as np
import pandas as pd
import random
import itertools
import json
import math
import pprint as pp
from numpy import loadtxt
from os import path
import matplotlib.pyplot as plt
import matplotlib as mpl


#### preliminaries ####

#def generate_embedding(query):
#    model = SentenceTransformer("l3cube-pune/indic-sentence-similarity-sbert")
#    query_embed = model.encode([query])
#    return query_embed


plaintext = []
all_embeddings = []
text_labels = []
    
# gujarati test set; 3075 test messages 

print("reading embedding file...")

with open('out.json', 'r') as f:
    for idx, line in enumerate(f):
        data = json.loads(line)
        embedding = data['embedding']
        text_label = data['text']
        all_embeddings.append(embedding)
        text_labels.append(text_label.rstrip('\n'))

embeddings = []
for i in range(1024):
    embeddings.append(all_embeddings[i])

print("done.")

# 1a ) generate scaled embeddings for query vectors and corpus

# current range is -0.3453960418701172 0.1843394786119461

print("scaling embeddings...")

query_embed = np.array(embeddings[0])

scaled_embeddings = []

for i in range(len(embeddings)):
    scaled_embeddings.append((np.array(embeddings[i]) * 1.5) + 0.6);

print("done.")

# 1b ) find distance between scaled embeddings and scaled query vectors

ground_truths = []
scaled_dists_grounds = []

for i in range(len(embeddings)):
    
    ground_truth = distance.euclidean(embeddings[0], embeddings[i])
    
    scaled_dists_ground = distance.euclidean(scaled_embeddings[0], scaled_embeddings[i])
   
    scaled_dists_grounds.append(scaled_dists_ground**2)
    ground_truths.append(ground_truth**2)
    

# 2a ) create projected vector embeddings (to ball radius = 1)

# 768 gives eps 0.3
# 512 gives eps 0.38
# 256 gives 0.6

print("generating transformed embeddings...")

transformer_five = random_projection.GaussianRandomProjection(n_components=512, eps = 0.38)
transformed_five = transformer_five.fit_transform(scaled_embeddings)

print("done.")


# 2b ) find squared L2 distances between query vector and each random vector in _res_ for ground-truth (un-projected) embeddings and all three epsilons

ep_fives = []

for i in range(len(embeddings)):
    ep_five = distance.euclidean(transformed_five[0], transformed_five[i])
    
    ep_fives.append(ep_five**2)


# 3a ) generated noised embeddings 0.42 (for n = 512), 0.67 (for n = 256), > 1 (for n = 128)

print("generating noised embeddings...")

def sigma(epsilon, delta, c=1, w=1):
    return c * w * np.sqrt(2 * (np.log(1/(2*delta)) + epsilon)) / epsilon # log is ln

eps6_noised_embeddings_five = []

five_noise_stddev_eps6 = sigma(6, 2**(-40), 1, 1/(np.sqrt(512)))
five_noise_eps6 = np.random.normal(0, five_noise_stddev_eps6, 512)

for i in range(len(scaled_embeddings)):

    five_noise_embed_eps6 = transformed_five[i] + five_noise_eps6
    eps6_noised_embeddings_five.append(five_noise_embed_eps6)

print("done.")


# 3b ) find squared L2 distances between query vectors and noised embeddings 0.42 (for n = 512), 0.67 (for n = 256), > 1 (for n = 128)

noised_five_dists_eps6 = []


print("generating benchmark.tsv...")

for i in range(len(embeddings)):
    
    noised_five_dist_eps6 = distance.euclidean(transformed_five[0], eps6_noised_embeddings_five[i])
    noised_five_dists_eps6.append(noised_five_dist_eps6**2)
    

df = pd.DataFrame(data=np.column_stack((ground_truths, scaled_dists_grounds, ep_fives, noised_five_dists_eps6)),
                  columns=['ground_truth', 'ground_truth_scaled', 'five_transform', 	        'five_noised_eps6'])

df.to_csv('benchmarks.tsv', sep = '\t', index = None)

print("done.")


print("generating query and embedding files...")

query_rep = []

for i in range(1024):
    query_rep.append(transformed_five[0])
    
query_arr = np.array(query_rep)

query_rep_df = pd.DataFrame(query_arr, index = None)

query_rep_df.to_csv('query.tsv', index = None, sep = '\t', header = None)

eps6_five = pd.DataFrame(eps6_noised_embeddings_five)
eps6_five.to_csv('database.tsv', sep = '\t', index = None, header = False)

print("done.")
