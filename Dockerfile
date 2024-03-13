FROM ghcr.io/blakeblackshear/frigate:stable

RUN pip install --upgrade pip \
    pip install schedule \
    pip install --upgrade openvino