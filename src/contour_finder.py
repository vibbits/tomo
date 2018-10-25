import numpy as np
import math

class ContourFinder:

    def optimize_contour(self, image, initial_contour, h_for_gradient_approximation=0.1, max_iterations=20, gradient_step_size=0.001):
        """

        :param image: preprocessed overview image with the ribbons of slices
        :param initial_contour: list of (x,y) vertex coordinates
        :param h_for_gradient_approximation: used for numeric gradient approximation: gradient = (f(x+h)-f(x)) / h
        :param max_iterations: the maximum number of iterations of gradient descent that will be performed to improve the slice contour
        :param gradient_step_size: the distance to move along the gradient during each iteration of gradient descent
        :return: optimized contour    # FIXME: what if there is not really a contour in that neighborhood of the image? return score too, so we can compare it to the score of the initial contour somehow?
        """
        iteration = 0
        current_contour = initial_contour  # CHECKME: deep copy needed?

        current_contour_vector = self.contour_to_vector(current_contour)
        print('initial contour={} score={}'.format(current_contour_vector, self.calculate_contour_score(image, current_contour_vector)))

        while iteration < max_iterations:  # FIXME: and gradient (or score?) is still changing
            gradient_vector = self._calculate_gradient(image, current_contour_vector, h_for_gradient_approximation)
            current_contour_vector = current_contour_vector - gradient_step_size * gradient_vector   # we are looking for a minimum of the score, so we move along the negative gradient
            print('iteration {} contour={} score={}'.format(iteration, current_contour_vector, self.calculate_contour_score(image, current_contour_vector)))
            # note: the gradient points towards higher values of the function
            iteration += 1

        return self.vector_to_contour(current_contour_vector)

    def preprocess_image(self, image):
        # TODO: e.g. blur image, remove dark specks, etc.
        return image

    def contour_to_vector(self, contour):
        """
        Turn a list of vertex coordinates of a contour into a numpy row vector. Useful for optimization algorithms such as gradient descent.
        :param contour: a list of vertex coordinates [(x1, y2), (x2, y2), ..., (xn, yn)] representing a contour
        :return: a numpy row vector [x1, y1, x2, y2, ..., xn, yn]
        """
        num_vertices = len(contour)
        vec = np.zeros(2 * num_vertices)
        for i in range(0, num_vertices):
            x, y = contour[i]
            vec[2 * i    ] = x
            vec[2 * i + 1] = y
        return vec

    def vector_to_contour(self, vec):
        """
        :param vec: a numpy row vector representation [x1, y1, x2, y2, ..., xn, yn] of a contour
        :return: a list of vertex coordinates [(x1, y2), (x2, y2), ..., (xn, yn)]
        """
        dim = len(vec)
        assert(dim % 2 == 0)
        pts = list(vec.reshape((dim / 2, 2)))   # lst = [np.array([x1, y1]), ..., np.array([xn,yn])]
        return [tuple(p) for p in pts]          # [(x1,y1),...,(xn,yn)]

    def _calculate_gradient(self, image, contour_vector, h = 0.1):
        """
        XXXX
        :param image: XXX
        :param contour_vector: a numpy row vector representation [x1, y1, x2, y2, ..., xn, yn] of a contour
        :param h: stepsize of numerical approximation of the gradient
        :return: a numpy row vector representation of the gradient of the contour's score
                 # XXXX for a quadrilateral slice contour this is (dscore/dx1, dscore/dy1, dscore/dx2, dscore/dy2,...,dscore/dx4, dscore/dy4)
        """
        n = len(contour_vector)
        assert(n % 2 == 0)

        gradient = np.zeros(n, np.float)
        contour_score = self.calculate_contour_score(image, contour_vector)
        for i in range(0, n):
            # Build displacement vector, it only displaces a single x or y coordinate
            delta = np.zeros(n, np.float)
            delta[i] = h

            # Calculate score if one endpoint is displaced slightly
            dispaced_contour_score = self.calculate_contour_score(image, contour_vector + delta)

            # Numerically estimate the gradient in the i-th direction
            gradient[i] = (dispaced_contour_score - contour_score) / h

        return gradient

    def calculate_contour_score(self, image, contour_vector):
        """
        XXX
        :param image:
        :param contour_vector: XXX (note:
        :return:
        """
        n = len(contour_vector)
        assert(n % 2 == 0)
        score = 0.0
        for i in range(0, n, 2):  # e.g. if n==8 we get i = 0, 2, 4, 6
            x1 = contour_vector[ i         ]
            y1 = contour_vector[ i + 1     ]
            x2 = contour_vector[(i + 2) % n]
            y2 = contour_vector[(i + 3) % n]
            score += self._calculate_segment_score(image, (x1, y1), (x2, y2))
        return score

    def _calculate_segment_score(self, image, p1, p2):
        """
        XXXX
        :param image: XXX
        :param p1: a pair (x1, y1), coordinates of the starting point of the segment
        :param p2: a pair (x2, y2), coordinates of the end point of the segment
        :return: XXX
        """
        approx_distance_between_samples = 10.0  # sample approximately every pixel, TODO: make parameter?
        v1 = np.array(p1)
        v2 = np.array(p2)
        distance_v1_v2 = math.sqrt(sum((v2 - v1) ** 2))
        if distance_v1_v2 <= approx_distance_between_samples:
            pos = 0.5 * (v1 + v2)
            return self._sample_image(image, pos) * distance_v1_v2
        else:
            num_samples = int(distance_v1_v2 / approx_distance_between_samples)
            assert(num_samples > 0)
            exact_distance_between_samples = distance_v1_v2 / num_samples
            # this splits the line segment exactly in 'num_samples' equally long sections of the line segment
            # IMPROVEME: this does not sample the end points of the line segment; somewhat unfortunate, it means we don't sample the corners of the slice contours - maybe we should fix that
            score = 0.0
            sample_weight = distance_v1_v2 / num_samples
            for i in range(num_samples):
                pos = v1 + ((i + 0.5) * exact_distance_between_samples / distance_v1_v2) * (v2 - v1)
                score += self._sample_image(image, pos) * sample_weight
            # print('{} to {} score={}'.format(p1, p2, score))
            return score

    def _sample_image(self, image, pos):
        """

        :param image: an OpenCV grayscale image, image[0][0] is the top left pixel, the first index is the y-coordinate, y-axis points down
        :param pos: (x, y) position in the image; x and y are floating point; x=horizontal, y=vertical  TODO: where is the origin? top left of image with y-axis running down?
        :return:
        """

        assert(pos[1] >= 0)

        # TODO: truncate pos to the image boundaries

        x_left = int(pos[0])
        x_right = x_left + 1

        y_top = int(pos[1])
        y_bottom = y_top + 1

        x_fraction = pos[0] - x_left
        y_fraction = pos[1] - y_top

        # bilinear interpolation (val is the image intensity)
        val_top    = image[y_top   ][x_left] + x_fraction * (image[y_top   ][x_right] - image[y_top   ][x_left])
        val_bottom = image[y_bottom][x_left] + x_fraction * (image[y_bottom][x_right] - image[y_bottom][x_left])
        val = val_top + y_fraction * (val_bottom - val_top)

        return val