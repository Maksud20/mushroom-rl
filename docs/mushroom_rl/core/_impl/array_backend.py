import numpy as np
import torch

from mushroom_rl.utils.torch import TorchUtils


class ArrayBackend(object):
    @staticmethod
    def get_backend_name():
        raise NotImplementedError

    @staticmethod
    def get_array_backend(backend):
        if backend == 'numpy':
            return NumpyBackend
        elif backend == 'torch':
            return TorchBackend
        else:
            return ListBackend

    @classmethod
    def convert(cls, *arrays, to='numpy'):
        if to == 'numpy':
            return cls.arrays_to_numpy(*arrays)
        elif to == 'torch':
            return cls.arrays_to_torch(*arrays)
        else:
            return NotImplementedError

    @classmethod
    def arrays_to_numpy(cls, *arrays):
        return (cls.to_numpy(array) for array in arrays)

    @classmethod
    def arrays_to_torch(cls, *arrays):
        return (cls.to_torch(array) for array in arrays)

    @staticmethod
    def to_numpy(array):
        return NotImplementedError

    @staticmethod
    def to_torch(array):
        raise NotImplementedError

    @staticmethod
    def to_backend_array(cls, array):
        raise NotImplementedError

    @staticmethod
    def zeros(*dims, dtype):
        raise NotImplementedError

    @staticmethod
    def ones(*dims, dtype):
        raise NotImplementedError

    @staticmethod
    def copy(array):
        raise NotImplementedError

    @staticmethod
    def pack_padded_sequence(array, lengths):
        raise NotImplementedError


class NumpyBackend(ArrayBackend):
    @staticmethod
    def get_backend_name():
        return 'numpy'

    @staticmethod
    def to_numpy(array):
        return array

    @staticmethod
    def to_torch(array):
        return None if array is None else torch.from_numpy(array).to(TorchUtils.get_device())

    @staticmethod
    def to_backend_array(cls, array):
        return cls.to_numpy(array)

    @staticmethod
    def zeros(*dims, dtype=float):
        return np.zeros(dims, dtype=dtype)

    @staticmethod
    def ones(*dims, dtype=float):
        return np.ones(dims, dtype=dtype)

    @staticmethod
    def copy(array):
        return array.copy()

    @staticmethod
    def pack_padded_sequence(array, lengths):
        shape = array.shape

        new_shape = (shape[0] * shape[1],) + shape[2:]
        mask = (np.arange(len(array))[:, None] < lengths[None, :]).flatten(order='F')
        return array.reshape(new_shape, order='F')[mask]


class TorchBackend(ArrayBackend):
    @staticmethod
    def get_backend_name():
        return 'torch'

    @staticmethod
    def to_numpy(array):
        return None if array is None else array.detach().cpu().numpy()

    @staticmethod
    def to_torch(array):
        return array

    @staticmethod
    def to_backend_array(cls, array):
        return cls.to_torch(array)

    @staticmethod
    def zeros(*dims, dtype=torch.float32):
        return torch.zeros(*dims, dtype=dtype, device=TorchUtils.get_device())

    @staticmethod
    def ones(*dims, dtype=torch.float32):
        return torch.ones(*dims, dtype=dtype, device=TorchUtils.get_device())

    @staticmethod
    def copy(array):
        return array.clone()

    @staticmethod
    def pack_padded_sequence(array, lengths):
        shape = array.shape

        new_shape = (shape[0]*shape[1], ) + shape[2:]
        mask = (torch.arange(len(array), device=TorchUtils.get_device())[None, :] < lengths[:, None]).flatten()
        return array.transpose(0,1).reshape(new_shape)[mask]


class ListBackend(ArrayBackend):
    @staticmethod
    def get_backend_name():
        return 'list'

    @staticmethod
    def to_numpy(array):
        return np.array(array)

    @staticmethod
    def to_torch(array):
        return None if array is None else torch.as_tensor(array, device=TorchUtils.get_device())

    @staticmethod
    def to_backend_array(cls, array):
        return cls.to_numpy(array)

    @staticmethod
    def zeros(*dims, dtype=float):
        return np.zeros(dims, dtype=float)

    @staticmethod
    def ones(*dims, dtype=float):
        return np.ones(dims, dtype=float)

    @staticmethod
    def copy(array):
        return array.copy()

    @staticmethod
    def pack_padded_sequence(array, lengths):
        return NumpyBackend.pack_padded_sequence(array, lengths)




