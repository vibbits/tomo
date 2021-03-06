import numpy as np
import math
import tools

class ContourFinder:

    def __init__(self):
        self.h_for_gradient_approximation = 1.0
        self.max_iterations = 50
        self.gradient_step_size = 5e-3
        self.edge_sample_distance = 50.0
        self.vertex_distance_threshold = 0.5
        self.verbose = False

    def set_optimization_parameters(self, h_for_gradient_approximation, max_iterations, vertex_distance_threshold, gradient_step_size, edge_sample_distance, verbose):
        """
        XXX
        :param h_for_gradient_approximation: step size h used for numeric gradient approximation: gradient = (f(x+h)-f(x)) / h
        :param max_iterations: the maximum number of iterations of gradient descent that will be performed to improve the slice contour
        :param vertex_distance_threshold: if during an iteration of the iterative process of improving the slice polygon shape,
               all vertices moved less than this threshold distance, then we assume we're close to the optimum contour shape and stop iterating.
        :param gradient_step_size: the distance to move along the gradient during each iteration of gradient descent
        :param edge_sample_distance: XXX
        :param verbose: XXX
        """
        self.h_for_gradient_approximation = h_for_gradient_approximation
        self.max_iterations = max_iterations
        self.vertex_distance_threshold = vertex_distance_threshold
        self.gradient_step_size = gradient_step_size
        self.edge_sample_distance = edge_sample_distance
        self.verbose = verbose

    def optimize_contour(self, image, initial_contour):
        """
        :param image: preprocessed overview image with the ribbons of slices
        :param initial_contour: list of (x,y) vertex coordinates
        :return: optimized contour, as list of (x,y) vertex coordinates
        """

        # We are trying to maximize the score. The score is measured in the preprocessed overview image,
        # where edges are white (high intensity value = high score) and background black (low intensity value = low score).
        # So edge pixels in the preprocessed image score many points, background pixels few points.

        iteration = 0
        vertex_distance_change = 10 * self.vertex_distance_threshold  # 10 just to initialize to something larger than the initial threshold
        previous_contour_vector = contour_to_vector(initial_contour)

        current_contour = initial_contour
        current_contour_vector = contour_to_vector(current_contour)

        while vertex_distance_change > self.vertex_distance_threshold and iteration < self.max_iterations:
            gradient_vector = self._calculate_gradient(image, current_contour_vector)
            current_contour_vector = current_contour_vector + self.gradient_step_size * gradient_vector   # we are looking for a maximum of the score, so we move along the positive gradient
            if self.verbose:
                print('Contour update: gradient step size={} pos update={}'.format(self.gradient_step_size, self.gradient_step_size * gradient_vector))
                print('Iteration {} score={}'.format(iteration, self.calculate_total_contour_score(image, current_contour_vector)))
            # note: the gradient points towards higher values of the function
            vertex_distance_change = np.max(_vertex_distances(previous_contour_vector, current_contour_vector))
            # print('   iteration={} change={}'.format(iteration, vertex_distance_change))
            previous_contour_vector = current_contour_vector
            iteration += 1

        if self.verbose:
            initial_score = self.calculate_total_contour_score(image, contour_to_vector(initial_contour))
            final_score = self.calculate_total_contour_score(image, current_contour_vector)
            print('Original score={} optimized score after {} iterations={} last max vertex displacement={}'.format(initial_score, iteration, final_score, vertex_distance_change))

        return vector_to_contour(current_contour_vector)

    def _calculate_gradient(self, image, contour_vector):
        """
        Returns an estimate of the gradient of the contour score function.
        The gradient is approximated as (f(x+h) - f(x)) / h
        IMPROVEME? (f(x+h/2)-f(x-h/2))/h is a more accurate estimate

        :param image: a preprocessed overview image; ideally this image should have (i) high pixel intensity at slice
        contour edges and low intensity for background and inside the sections,
        (ii) little noise and debris, (iii) an intensity profile that starts relatively "far" from edges and
        increases smoothly towards the edge center.
        :param contour_vector: a numpy row vector representation [x1, y1, x2, y2, ..., xn, yn] of a contour
        :return: a numpy row vector representation of the gradient of the contour's score;
                 for a quadrilateral slice contour this is [dscore/dx1, dscore/dy1, dscore/dx2, dscore/dy2,...,dscore/dx4, dscore/dy4]
        """
        n = len(contour_vector)
        assert(n % 2 == 0)

        h = self.h_for_gradient_approximation

        gradient = np.zeros(n, np.float)
        contour_score = self.calculate_total_contour_score(image, contour_vector)
        for i in range(0, n):
            # Build displacement vector, it only displaces a single x or y coordinate
            delta = np.zeros(n, np.float)
            delta[i] = h

            # Calculate score if one endpoint is displaced slightly
            dispaced_contour_score = self.calculate_total_contour_score(image, contour_vector + delta)

            # Numerically estimate the gradient in the i-th direction
            gradient[i] = (dispaced_contour_score - contour_score) / h

        return gradient

    def calculate_contour_score_samples(self, image, contour_vector):
        """
        XXX
        :param image:
        :param contour_vector:
        :return: a list of n (4 in our case) lists; each of the n lists holds the score samples along the n contour edges
        """
        n = len(contour_vector)
        assert(n % 2 == 0)
        scores = [[] for i in range(n // 2)]
        for i in range(0, n, 2):  # e.g. if n==8 we get i = 0, 2, 4, 6
            x1 = contour_vector[ i         ]
            y1 = contour_vector[ i + 1     ]
            x2 = contour_vector[(i + 2) % n]
            y2 = contour_vector[(i + 3) % n]
            scores[i // 2] = self._calculate_segment_score_samples(image, (x1, y1), (x2, y2))
        return scores

    def calculate_total_contour_score(self, image, contour_vector):
        """

        :param image:
        :param contour_vector:
        :return: the total score of the contour (a scalar value); contours with a larger score a more likely to represent a true section contour
        """
        segment_scores = self.calculate_contour_score_samples(image, contour_vector)
        return np.sum(np.sum(segment_scores))  # total score is the sum of all score samples, obtained over all contour edges

    def _calculate_segment_score_samples(self, image, p1, p2):
        """
        XXXX
        :param image: XXX
        :param p1: a pair (x1, y1), coordinates of the starting point of the segment
        :param p2: a pair (x2, y2), coordinates of the end point of the segment
        :return: a list with score samples along the line segment p1-p2
        """
        # TODO?
        # Perhaps experiment with a score function that is a weighed version of the current score and a scalar value that measures how
        # much the shape of the slice contour resembles the shape of a template slice contour.

        v1 = np.array(p1)
        v2 = np.array(p2)
        distance_v1_v2 = math.sqrt(sum((v2 - v1) ** 2))
        direction = (v2 - v1) / distance_v1_v2

        # Collect equidistant image samples along the edge p1p2.
        # The first sample is collected in edge start point p1, but no sample is collected on the end point side of the edge (near p2).
        # This way, for a closed contour, calling this method on each edge in turn will nicely sample all vertices of the polygon.

        approx_distance_between_samples = self.edge_sample_distance
        num_samples = max(1, int(distance_v1_v2 / approx_distance_between_samples))
        exact_distance_between_samples = distance_v1_v2 / num_samples

        # 1) One possible scoring function which works
        # sample_weight = distance_v1_v2 / num_samples

        # 2) Below is another scoring function, which seems to work better in a ribbon-growing experiment.
        #    The factor 1000 was needed so that the other parameters such as gradient descent step size etc
        #    could be preserved as is (compared to the score that is proportional to the distance between p1 and p2).
        sample_weight = 1000.0 / num_samples

        scores = [0.0] * num_samples
        for i in range(num_samples):
            pos = v1 + i * exact_distance_between_samples * direction
            scores[i] = tools.sample_image(image, pos) * sample_weight
        return scores
        # FIXME / CHECKME: Is the score normalized by contour length? If not, change this, I think it should be.
        # (If we don't normalize, then perhaps the optimization will prefer slightly bigger contours
        # that collect less score per sample, over smaller but more accurate contours that collect more score per sample, but less overall?)

def contour_to_vector(contour):
    """
    Turn a list of vertex coordinates of a contour into a numpy row vector. Useful for optimization algorithms such as gradient descent.
    :param contour: a list of vertex coordinates [(x1, y1), (x2, y2), ..., (xn, yn)] or [np.array([x1,y 1]), ..., np.array([xn, yn])] representing a contour
    :return: an equivalent numpy row vector [x1, y1, x2, y2, ..., xn, yn]
    """
    num_vertices = len(contour)
    vec = np.zeros(2 * num_vertices)
    for i in range(0, num_vertices):
        x, y = contour[i]
        vec[2 * i    ] = x
        vec[2 * i + 1] = y
    return vec


def vector_to_contour(vec):
    """
    :param vec: a numpy row vector representation [x1, y1, x2, y2, ..., xn, yn] of a contour
    :return: an equivalent list of vertex coordinate pairs [(x1, y2), (x2, y2), ..., (xn, yn)]
    """
    dim = len(vec)
    assert(dim % 2 == 0)
    pts = list(vec.reshape((dim / 2, 2)))   # lst = [np.array([x1, y1]), ..., np.array([xn,yn])]
    return [tuple(p) for p in pts]          # [(x1,y1),...,(xn,yn)]


def _vertex_distances(contour1, contour2):
    # contour1 and 2 are numpy row vectors [x1, y1, x2, y2, ..., xn, yn] where n=number of vertices (=4 because are sections are quadrilaterals)
    # returns a numpy array (with n elements) with the Euclidean distance between corresponding vertices in the two contours
    difference = contour1.reshape(-1, 2) - contour2.reshape(-1, 2)  # reshape to an nx2 matrix (so each row is the x,y of a vertex), and subtract
    distances = np.linalg.norm(difference, axis=1)  # distances[i] = euclidean distances between vertex i in contour1 and contour2
    return distances


