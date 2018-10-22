
import numpy as np

# Reference:
# Scattered data interpolation methods for electronic imaging systems: a survey
# Isaac Amidror
# Journal of Electronic Imaging 11(2), 157--176 (April 2002)
# http://molly.magic.rit.edu/~mac/test/paper_pdf.pdf
# We do inverse distance weighing, see section 3 in this paper.

class ScatteredDataInterpolator:
    _data = []
    def __init__(self, data, k = 1.0):
        """
        XXXXX
        :param data: an n x 3 numpy array; each row is a data point, and the columns are x, y and z respectively; given a new (x,y) we want to calculate an interpolated z
        :param k: exponent for inverse distance weigthing function; k >= 1; larger k yields an interpolated surface with bigger "plateaus" around the sample points
        """
        assert k >= 1.0
        self._k = k
        self._data = data

    def interpolate(self, pos, eps = 1e-9):
        """
        XXXX
        :param pos:
        :param eps:
        :return:
        """
        posi = self._data[:, 0:2]
        di = np.sqrt(np.sum((posi - pos) ** 2, axis = 1))  # di = Euclidean distance from pos to each data point

        # Check for the special case where pos is really close to a data point, because there d ~= 0 and h ~= infinite.
        index = np.argmin(di)
        di_min = di[index]
        if di_min < eps:
            z = self._data[index, 2]   # pos is very close to a data point, simply return its z
        else:
            hi = 1.0 / (di ** self._k) # hi = inverse distances
            wi = hi / np.sum(hi)       # wi = interpolation weights
            # print(np.sum(wi))          # FOR TESTING - SHOULD BE 1
            zi = self._data[:, 2]      # zi = sample data z
            z = np.dot(wi, zi)         # z = inverse distance weighted

        return z

if __name__ == '__main__':

    # Example 1: 2 scatter points
    
    data = np.array([[0, 0, 0],
                     [100, 100, 1]])
    print(data)

    sdi = ScatteredDataInterpolator(data, k=1)

    p1 = np.array([  0,   0]); print(p1, sdi.interpolate(p1))
    p3 = np.array([100, 100]); print(p3, sdi.interpolate(p3))

    p8 = np.array([10, 10]); print(p8, sdi.interpolate(p8))
    p6 = np.array([25, 25]); print(p6, sdi.interpolate(p6))
    p7 = np.array([50, 50]); print(p7, sdi.interpolate(p7))
    p2 = np.array([75, 75]); print(p2, sdi.interpolate(p2))

    p4 = np.array([  200,   200]); print(p4, sdi.interpolate(p4))
    p5 = np.array([ 2000,  2000]); print(p5, sdi.interpolate(p5))

    # Example 2: 4 scatter points

    data2 = np.array([[  0,   0, 0],
                      [100,   0, 2],
                      [  0, 100, 1],
                      [100, 100, 1]])
    print(data2)

    sdi = ScatteredDataInterpolator(data2, k=1)

    p1 = np.array([  0,   0]); print(p1, sdi.interpolate(p1))
    p3 = np.array([100, 100]); print(p3, sdi.interpolate(p3))

    p8 = np.array([10, 10]); print(p8, sdi.interpolate(p8))
    p6 = np.array([25, 25]); print(p6, sdi.interpolate(p6))
    p7 = np.array([50, 50]); print(p7, sdi.interpolate(p7))  # returns the average of the values at the 4 points
    p2 = np.array([75, 75]); print(p2, sdi.interpolate(p2))

    p4 = np.array([  200,   200]); print(p4, sdi.interpolate(p4))
    p5 = np.array([ 2000,  2000]); print(p5, sdi.interpolate(p5))
