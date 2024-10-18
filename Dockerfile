FROM ghcr.io/blakeblackshear/frigate:0.13.2
# FROM ghcr.io/blakeblackshear/frigate:stable-tensorrt

RUN \
    # pip install --upgrade pip \
    # pip install schedule \
    pip install --upgrade openvino

RUN apt update && apt install -y zstd

# RUN cd $(mktemp -d)

# RUN wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-1.0.16510.2/intel-igc-core_1.0.16510.2_amd64.deb
# RUN wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-1.0.16510.2/intel-igc-opencl_1.0.16510.2_amd64.deb
# RUN wget https://github.com/intel/compute-runtime/releases/download/24.13.29138.7/intel-level-zero-gpu-dbgsym_1.3.29138.7_amd64.ddeb
# RUN wget https://github.com/intel/compute-runtime/releases/download/24.13.29138.7/intel-level-zero-gpu_1.3.29138.7_amd64.deb
# RUN wget https://github.com/intel/compute-runtime/releases/download/24.13.29138.7/intel-opencl-icd-dbgsym_24.13.29138.7_amd64.ddeb
# RUN wget https://github.com/intel/compute-runtime/releases/download/24.13.29138.7/intel-opencl-icd_24.13.29138.7_amd64.deb
# RUN wget https://github.com/intel/compute-runtime/releases/download/24.13.29138.7/libigdgmm12_22.3.18_amd64.deb

# RUN dpkg -i --force-all --ignore-depends=/usr/lib/x86_64-linux-gnu/libze_intel_gpu.so.1 *.deb