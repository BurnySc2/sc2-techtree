FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    git \
    make \
    libfuse-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src/stormex

RUN git clone --recurse-submodules https://github.com/Talv/stormex . && \
    printf '#include <string>\nint cascfs_mount(const std::string&, void*) { return 1; }' > src/cascfuse_stub.cc && \
    sed -i 's/src\/cascfuse.cc/src\/cascfuse_stub.cc/' CMakeLists.txt && \
    mkdir -p build && \
    cd build && \
    cmake .. -DENABLE_FUSE=OFF && \
    make -j$(nproc)

FROM ubuntu:20.04

COPY --from=0 /src/stormex/build/bin/stormex /usr/local/bin/stormex

WORKDIR /data
ENTRYPOINT ["stormex"]
