import json

import numpy as np

# Note: this is certainly NOT a fully general way to serialize general numpy arrays to JSON,
#       it only works for the relatively easy cases we need it for.


class JSONNumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):  # is it a numpy array or matrix?
            return {'__numpy.ndarray__': True,  # We store the matrix elements inside a dictionary with extra metadata, so that when reading the JSON object we realize that the dictionary actually represents a numpy array
                    'dtype': str(obj.dtype),  # current unused
                    'dtype.name': obj.dtype.name,  # probably good enough for our simple numpy arrays
                    'shape': str(obj.shape),  # shape is probably redundant (can probably be recovered from the nesting structure of the lists in 'data')
                    'data': obj.tolist()}
        else:
            return super(JSONNumpyEncoder, self).default(obj)


def json_numpy_array_decoder(dct):
    if '__numpy.ndarray__' in dct:
        return np.array(dct['data'], dtype=dct['dtype.name'])
    else:
        return dct