# FROM ghcr.io/blakeblackshear/frigate:stable
FROM ghcr.io/blakeblackshear/frigate:stable-tensorrt

RUN pip install --upgrade pip \
    # pip install schedule \
    pip install --upgrade openvino