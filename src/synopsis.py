from Compiler.compilerLib import Compiler

from Compiler import mpc_math
from Compiler.instructions import *
from Compiler.util import if_else

from Compiler.types import sfix, sfloat, Array
from Compiler.util import if_else
from Compiler.library import for_range_opt, print_ln

# from laplace import apply_laplace_mechanism
import time


_DEBUG = True
print_secrets = True
compiler = Compiler()

# arithmetic funcs


# absolute value
def abs(v):
    # or just v.s = 1/0
    return v * ((v > 0) - (v < 0))


# sfix and sfloat ln
def ln(x):
    return mpc_math.log_fx(x, math.e)


# convert neg sign bool eval (0) to -1
def find_sign(v):
    return if_else(v < 0, -1, 1)


# translate unif-randomly drawn samples in the interval [-0.5, 0.5] to random draws from laplace distribution
def laplace_inverse_cdf(unif, scale):

    laplace_noise = Matrix(1, len(unif[0]), sfix)
    sign_corrected = Matrix(1, len(unif[0]), sfix)

    @for_range_opt(len(unif[0]))
    def _(i):
        sign_corrected[0][i] = find_sign(unif[0][i])

        unif_abs = abs(unif[0][i])

        laplace_noise[0][i] = -scale * sign_corrected[0][i] * ln(1 - 2 * unif_abs)

    return laplace_noise


# combine data vecs and laplace noise matrix
def apply_laplace_mechanism_one(vecs, eps, sen, phase):

    # scale is sensitivity over epsilon allowance
    scale = cfix(sen / eps)

    # FT queries: counts noising

    unif_sample = unif_random_gen(1, 1, 1, 1)

    noise_for_count = laplace_inverse_cdf(unif_sample, scale)

    noised_count = sfloat(vecs[0][0]) + sfloat(noise_for_count[0][0])

    return noised_count


# return n_vecs x vec_dim matrix of unif-randomly generated samples (for noising dataspace)
def unif_random_gen(bitlength, n_vecs, vec_dim, vec_length):

    bitlength = 3

    M = Matrix(1, vec_length, sfix)

    @for_range_opt(vec_length)
    def _(i):
        randint = sint.get_random_int(bitlength)

        # normalize to interval [0, 1] and shift 0.5 to left to obtain randint in [-0.5, 0.5]
        fraction = (sfix(randint) * sfix(2 ** (-bitlength))) - 0.5

        M[0][i] = fraction

    return M  # 1-dim matrix of sfloats


# apply distance (NOT eligible counts) threshold; accepts (1 x n) matrix and returns array
def apply_threshold(data, count_threshold):

    count_threshold = sfloat(count_threshold)
    eligible = Array(len(data), sint)
    eligible[0] = sint(0)
    eligible_arr = Array(len(data), sint)

    @for_range_opt(len(data))
    def _(i):
        eval_result = sint(data[i] < count_threshold).if_else(sint(1), sint(0))
        eligible[0] = eligible[0] + eval_result
        eligible_arr[i] = eval_result

    return eligible, eligible_arr


# generate duplicate/concatenated query vector
def pad_query(query, rows, cols):  # output size is query size x database size

    dup = rows

    # Duplicate and concatenate the vector
    padded_q = query * int(dup)

    return padded_q


# 2xq
def two_x_q(
    data, query
):  # output size is query size x database size; accepts two one-dim matrices

    composite = Array(len(data), sfix)

    total = len(data)

    print_ln("calculate 2xq")

    client = Array(1, sfix)

    # scalar doubling
    composite = [2 * a * b for a, b in zip(data, query)]

    return composite


# q^2
def squared_q(query):  # output size is query size

    print_ln("calculate q^2")

    q_squared = Array(int(len(query)), sfix)

    q_squared = [a * a for a, a in zip(query, query)]

    return q_squared


# string together (x - q) calculations
def find_dist(data, data_sq, query):  # accepts MultiArray and Matrix; returns Array

    # decompose squared diff into x^2 - 2xq + q^2
    # -- x^2 happens on intake, before querytime, and is a private x private calculation
    # -- 2xq happens during querytime, and is a private x public calculation
    # -- q^2 happens during querytime, and is a public x public calculation
    # as a further note, all operations are on a one-dim vector:
    # database elements are concatenated to this single-row vector, squared element-wise (x^2), multiplied modulo the size of the query vector (2xq)

    # query and dataspace as matrices of sfloats

    rows = len(data) / len(query)
    cols = len(query)

    print_ln("rows (number of database entries): %s", rows)
    print_ln("cols (size of embedding vector): %s", cols)

    padded_q = pad_query(query, rows, cols)

    two_ex_q = two_x_q(data, padded_q)

    q_squared = squared_q(padded_q)

    diffed = Array(int(rows * cols), sfix)
    diffed = [a - b + c for a, b, c in zip(data_sq, two_ex_q, q_squared)]

    # sum every sequence of [query-length]-element sfixes together

    sums = Matrix(1, int(rows), sfix)
    sums[0] = [sum(diffed[i : i + cols]) for i in range(0, len(data), cols)]

    return sums[0]


# FC query
def fc(data, data_sq, query, threshold, eps, sen):

    print_ln("---------------fine-grained count query-----------------")
    print_ln("epsilon budget: %s", eps)

    print_ln("begin distance calculation")
    dist_mat = find_dist(
        data, data_sq, query
    )  # returns (unnoised) 1xn IP matrix (diff dataspace and query vector)
    print_ln("begin thresholding")
    thresholded_count, threshold_arr = apply_threshold(
        dist_mat, threshold
    )  # returns array containing single element (eligible query counts)
    noised_count = apply_laplace_mechanism_one(
        thresholded_count, eps, sen, 1
    )  # returns noised query count

    print_ln("noised thresholded count: %s", noised_count.reveal())
    return noised_count


# CC query
def cc(data, data_sq, query, threshold):

    print_ln("---------------coarse-grained count query-----------------")

    rows = len(data) / len(query)
    cols = len(query)

    # find unnoised dists for error checking
    dist_start = time.time()
    true_mat = find_dist(data, data_sq, query)
    dist_stop = time.time()
    thresholded_count, thresholded_arr = apply_threshold(true_mat, threshold)

    print_ln("thresholded count: %s:", thresholded_count[0].reveal())
    return thresholded_count


# FT query
def ft(data, data_sq, query, ball_threshold, eps, sen, release_threshold):

    print_ln("---------------fine-grained threshold query-----------------")
    print_ln("epsilon budget: %s", eps)

    # calculate unthresholded count in secret
    dist_mat = find_dist(
        data, data_sq, query
    )  # returns (unnoised) 1xn IP matrix (diff dataspace and query vector)
    thresholded_count, threshold_arr = apply_threshold(
        dist_mat, ball_threshold
    )  # returns array containing single element (eligible query counts)
    noised_count = apply_laplace_mechanism_one(thresholded_count, eps, sen, 1)

    flag = sint(noised_count > release_threshold).if_else(1, 0)

    print_ln("thresholded result: %s", flag.reveal())

    return flag


# CT query
def ct(data, data_sq, query, ball_threshold, release_threshold):

    print_ln("---------------coarse-grained threshold query-----------------")

    # calculate unthresholded count in secret
    true_mat = find_dist(data, data_sq, query)
    thresholded_count, thresholded_arr = apply_threshold(true_mat, ball_threshold)

    flag = sint(thresholded_count[0] > release_threshold).if_else(1, 0)

    print_ln("thresholded result: %s", flag.reveal())

    return flag


# detailed error analysis (not currently called; call on threshold_arr in count queries to use)
def error_checking(y_true, y_pred):  # for coarse-grained queries only

    tn = Array(1, sfloat)
    tn[0] = sfloat(0)
    tp = Array(1, sfloat)
    tp[0] = sfloat(0)

    fp = Array(1, sfloat)
    fp[0] = sfloat(0)
    fn = Array(1, sfloat)
    fn[0] = sfloat(0)

    y_ip = Array(len(y_true), sfloat)
    y_diff = Array(len(y_true), sfloat)

    print_ln("len of y_true: %s", len(y_true))

    print_ln(
        "first and second elements of y_true: %s, %s",
        y_true[0].reveal(),
        y_true[1].reveal(),
    )

    @for_range_opt(len(y_true))
    def _(i):
        # inner product for checking TPs
        y_ip[i] = sint.dot_product(y_pred[i], y_true[i])

    @for_range_opt(len(y_true))
    def _(i):
        print_ln(
            "[%s] true value: %s ; predicted value: %s",
            i,
            y_true[i].reveal(),
            y_pred[i].reveal(),
        )
        y_diff[i] = y_true[i] - y_pred[i]

    @for_range_opt(len(y_ip))
    def _(i):
        tp[0] = tp[0] + y_ip[i]

    @for_range_opt(len(y_diff))
    def _(i):
        fn_count = (y_diff[i] == 1).if_else(sint(1), sint(0))
        fn[0] = fn[0] + fn_count

        fp_count = (y_diff[i] == -1).if_else(sint(1), sint(0))
        fp[0] = fp[0] + fp_count

    # total len - TP - FN - FP for TNs
    tn[0] = (len(y_true) - (tp[0] + fn[0] + fp[0])) / len(y_true)
    fn[0] = fn[0] / len(y_true)
    fp[0] = fp[0] / len(y_true)
    tp[0] = tp[0] / len(y_true)

    print_ln("tn rate: %s", tn[0].reveal())

    print_ln("tp rate: %s", tp[0].reveal())

    print_ln("fn rate: %s", fn[0].reveal())

    print_ln("fp rate: %s", fp[0].reveal())


@compiler.register_function("synopsis")
def synopsis():
    # ~~~~~~~~~~~~~~ file io ~~~~~~~~~~~~~~~~~#

    sfix.set_precision(16, 31)

    # 524288 for full sample database, dim 1024 x 512
    database = Array(524288, sfix)  # database only
    database_sq = Array(524288, sfix)

    # read vectors from player 0
    @for_range_opt(524288)
    def _(i):
        # for j in range(1):
        database[i] = sfix.get_input_from(0)

    # read squared database from player 1
    @for_range_opt(524288)
    def _(i):
        database_sq[i] = sfix.get_input_from(1)

    # ~~~~~~~~~~~~~~~ generate test data ~~~~~~~~~~~~~~~#

    from .query import query_clear

    # database = Array(30000, sfix)

    # query_secret = Matrix(1, 500, sfix)

    # 512-dim public query

    # 300-dim public query
    # query_clear = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # for random-gen database
    # @for_range_opt(30000)
    # def _(j):
    #   database[j] = sfix(random.uniform(0, 1))
    # randgen_stop = time.time()
    # print_ln("randgen timing: %s", randgen_stop - randgen_start)

    # ~~~~~~~~~~~~~~ calls ~~~~~~~~~~~~~~~#

    # function calls for all query types take the following form:

    fc_test = fc(database, database_sq, query_clear, 1.3, 4, 1)

    cc_test = cc(database, database_sq, query_clear, 1.3)

    ft_test = ft(database, database_sq, query_clear, 1.3, 4, 1, 5)

    ct_test = ct(database, database_sq, query_clear, 1.3, 5)


def run():
    compiler.compile_func()
    # figure out how to send arguments to this
    compiler.local_execution()
