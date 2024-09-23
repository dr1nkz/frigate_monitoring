FROM ghcr.io/blakeblackshear/frigate:0.13.2
# FROM ghcr.io/blakeblackshear/frigate:stable-tensorrt

RUN pip install --upgrade pip \
    pip install schedule \
    pip install --upgrade openvino