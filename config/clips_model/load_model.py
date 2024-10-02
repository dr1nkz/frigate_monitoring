import numpy as np
import tensorrt as trt

# Загрузка модели TensorRT
def load_engine(engine_path):
    with open(engine_path, 'rb') as f:
        engine = trt.Runtime(trt.Logger(trt.Logger.WARNING)).deserialize_cuda_engine(f.read())
    return engine

# Выполнение инференса
def infer(engine, input_data):
    with engine.create_execution_context() as context:
        # Подготовка входных данных
        inputs = np.array(input_data, dtype=np.float32)
        outputs = np.empty((1, output_size), dtype=np.float32)  # Измените output_size на нужный размер

        # Запуск инференса
        context.execute_v2(bindings=[inputs.ctypes.data, outputs.ctypes.data])
        return outputs

# Основной процесс
if __name__ == '__main__':
    engine = load_engine('model.trt')
    input_data = np.random.rand(1, input_size).astype(np.float32)  # Убедитесь, что размерность соответствует вашей модели
    output_data = infer(engine, input_data)
    print("Output data:", output_data)