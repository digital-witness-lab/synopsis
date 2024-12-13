# TODO:
#   - Make -DINSECURE flag a build-arg and do proper offline if we are not
#   faking it
ARG CRYPTO_PLAYERS=2
ARG MP_SPDZ_TAG=v0.4.0
ARG MP_SPDZ_HOME=/usr/src/MP-SPDZ
ARG PYTHON_TAG=3.13-slim-bullseye

#
# BUILD MP-SPDZ
#
# buildenv based off of https://github.com/data61/MP-SPDZ/blob/master/Dockerfile
FROM python:${PYTHON_TAG} AS build-mp-spdz

RUN apt-get update && apt-get install -y --no-install-recommends \
                automake \
                build-essential \
                clang-11 \
		        cmake \
                git \
                libboost-dev \
                libboost-thread-dev \
                libclang-dev \
                libgmp-dev \
                libntl-dev \
                libsodium-dev \
                libssl-dev \
                libtool \
        && rm -rf /var/lib/apt/lists/*

ARG MP_SPDZ_TAG
ARG MP_SPDZ_HOME
ENV MP_SPDZ_HOME=${MP_SPDZ_HOME}
ENV MP_SPDZ_TAG=${MP_SPDZ_TAG}
RUN git clone \
    --recurse-submodules \
    --branch ${MP_SPDZ_TAG} \
    "https://github.com/data61/MP-SPDZ.git" \
    ${MP_SPDZ_HOME}
WORKDIR $MP_SPDZ_HOME

ARG arch=
ARG cxx=clang++-11
ARG use_ntl=0
ARG prep_dir="Player-Data"
ARG ssl_dir="Player-Data"

RUN if test -n "${arch}"; then echo "ARCH = -march=${arch}" >> CONFIG.mine; fi
RUN echo "CXX = ${cxx}" >> CONFIG.mine &&\
    echo "USE_NTL = ${use_ntl}" >> CONFIG.mine && \
    echo "MY_CFLAGS += -I/usr/local/include -DINSECURE" >> CONFIG.mine && \
    echo "MY_LDLIBS += -Wl,-rpath -Wl,/usr/local/lib -L/usr/local/lib" >> CONFIG.mine && \
    echo "PREP_DIR = '-DPREP_DIR=\"${prep_dir}/\"'" >> CONFIG.mine && \
    echo "SSL_DIR = '-DSSL_DIR=\"${ssl_dir}/\"'" >> CONFIG.mine && \
    mkdir -p $prep_dir $ssl_dir

RUN make clean-deps boost libote

RUN make mascot-party.x && \
    make setup && \
    make Fake-Offline.x && \
    ./Scripts/setup-online.sh

ARG CRYPTO_PLAYERS
ENV PLAYERS=${CRYPTO_PLAYERS}
RUN ./Scripts/setup-ssl.sh "${CRYPTO_PLAYERS}" ${ssl_dir} && \
    ./Fake-Offline.x ${N_PLAYERS}


#
# RUNTIME
#

FROM python:${PYTHON_TAG} AS runtime

ARG CRYPTO_PLAYERS
ARG MP_SPDZ_TAG
ARG MP_SPDZ_HOME

ENV MP_SPDZ_HOME=${MP_SPDZ_HOME}
ENV MP_SPDZ_HOME=${MP_SPDZ_HOME}
ENV PYTHONPATH="${MP_SPDZ_HOME}:${PYTHONPATH}"

COPY --from=build-mp-spdz ${MP_SPDZ_HOME} ${MP_SPDZ_HOME}

COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /app
COPY . .
RUN pip install .

ENTRYPOINT ["synopsis"]
