FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS cuda

FROM ghcr.io/blakeblackshear/frigate:0.13.2

COPY --from=cuda /usr/local/cuda /usr/local/cuda
COPY --from=cuda /lib/x86_64-linux-gnu/libcudnn* /lib/x86_64-linux-gnu/

ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib:${LD_LIBRARY_PATH}
ENV PATH=/usr/local/cuda/bin:${PATH}

RUN echo "/usr/local/cuda/targets/x86_64-linux/lib" \
    > /etc/ld.so.conf.d/cuda.conf && ldconfig

RUN apt update && apt install -y libgl1

RUN pip install --no-cache-dir numpy==1.26 onnxruntime-gpu==1.18.1 shapely dotenv opencv-python
RUN pip install --upgrade openvino

COPY openvino.py /opt/frigate/frigate/detectors/plugins
COPY detector_rfdetr.py /opt/frigate/frigate/detectors/
COPY utils.py /opt/frigate/frigate/detectors/