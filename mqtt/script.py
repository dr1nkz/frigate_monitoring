# import torch
import onnxruntime

print(onnxruntime.get_available_providers())
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
path = '/mqtt/speed_estimation/yolov9c.onnx'
session = onnxruntime.InferenceSession(path, providers=providers)
