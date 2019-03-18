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

    def set_optimization_parameters(self, h_for_gradient_approximation, max_iterations, vertex_distance_threshold, gradient_step_size, edge_sample_distance):
        """
        XXX
        :param h_for_gradient_approximation: step size h used for numeric gradient approximation: gradient = (f(x+h)-f(x)) / h
               IMPROVEME? (f(x+h/2)-f(x-h/2))/h is probably a better estimate
        :param max_iterations: the maximum number of iterations of gradient descent that will be performed to improve the slice contour
        :param vertex_distance_threshold: if during an iteration of the iterative process of improving the slice polygon shape,
               all vertices moved less than this threshold distance, then we assume we're close to the optimum contour shape and stop iterating.
        :param gradient_step_size: the distance to move along the gradient during each iteration of gradient descent
        :param edge_sample_distance: XXX
        """
        self.h_for_gradient_approximation = h_for_gradient_approximation
        self.max_iterations = max_iterations
        self.vertex_distance_threshold = vertex_distance_threshold
        self.gradient_step_size = gradient_step_size
        self.edge_sample_distance = edge_sample_distance

    def optimize_contour(self, image, initial_contour):
        """
        :param image: preprocessed overview image with the ribbons of slices
        :param initial_contour: list of (x,y) vertex coordinates
        :return: optimized contour
        """
        iteration = 0
        vertex_distance_change = 10 * self.vertex_distance_threshold  # 10 just to initialize to something > the initial threshold
        previous_contour_vector = self.contour_to_vector(initial_contour)

        current_contour = initial_contour
        current_contour_vector = self.contour_to_vector(current_contour)

        while vertex_distance_change > self.vertex_distance_threshold and iteration < self.max_iterations:
            gradient_vector = self._calculate_gradient(image, current_contour_vector)
            current_contour_vector = current_contour_vector + self.gradient_step_size * gradient_vector   # we are looking for a maximum of the score, so we move along the positive gradient
            print('Contour update: gradient step size={} pos update={}'.format(self.gradient_step_size, self.gradient_step_size * gradient_vector))
            print('Iteration {} score={}'.format(iteration, self.calculate_contour_score(image, current_contour_vector)))
            # note: the gradient points towards higher values of the function
            vertex_distance_change = np.max(self._vertex_distances(previous_contour_vector, current_contour_vector))
            # print('   iteration={} change={}'.format(iteration, vertex_distance_change))
            previous_contour_vector = current_contour_vector
            iteration += 1

        print('Original score={} optimized score after {} iterations={} last max vertex displacement={}'.format(self.calculate_contour_score(image, self.contour_to_vector(initial_contour)), iteration, self.calculate_contour_score(image, current_contour_vector), vertex_distance_change))

        return self.vector_to_contour(current_contour_vector)

    def _vertex_distances(self, contour1, contour2):
        # contour1 and 2 are numpy row vectors [x1, y1, x2, y2, ..., xn, yn] where n=number of vertices (=4 because are sections are quadrilaterals)
        # returns a numpy array (with n elements) with the Euclidean distance between corresponding vertices in the two contours
        difference = contour1.reshape(-1, 2) - contour2.reshape(-1, 2)  # reshape to an nx2 matrix (so each row is the x,y of a vertex), and subtract
        distances = np.linalg.norm(difference, axis=1)  # distances[i] = euclidean distances between vertex i in contour1 and contour2
        return distances


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

    def _calculate_gradient(self, image, contour_vector):
        """
        XXXX
        :param image: XXX
        :param contour_vector: a numpy row vector representation [x1, y1, x2, y2, ..., xn, yn] of a contour
        :return: a numpy row vector representation of the gradient of the contour's score
                 # XXXX for a quadrilateral slice contour this is (dscore/dx1, dscore/dy1, dscore/dx2, dscore/dy2,...,dscore/dx4, dscore/dy4)
        """
        n = len(contour_vector)
        assert(n % 2 == 0)

        h = self.h_for_gradient_approximation

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
        :param contour_vector:
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
        # IMPROVEME?
        # This definition of score is not perfect: the algorithm tends to make the edges a bit too long:
        # the fact that this way less 'blackness' per pixel is collected, is compensated by the longer edges.
        # Maybe we ought to use some space-scale concept: the original edges get blurred relatively heavily to be able
        # to attract far away contour approximations. Then maybe after a couple of optimization iterations, when the contour is likely much closer
        # to its correct location, we switch to a less heavily blurred image. Due to the Gaussian intensity profile of the blurred edges,
        # a new equilibrium (closer to the true edge center) exists where the contour does not gain so much anymore from being longer
        # but passing through less dark pixels, and instead will move closer to the edge center again?
        # Or can we define a different score that does not have this undesirable effect of preferring too long edges?
        # TODO?
        # Perhaps experiment with a score function that is a weighed version of the current score and a scalar value that measures how
        # much the shape of the slice contour resembles the shape of a template slice contour.
        # TODO?
        # A common failure of the active contour seems to be that the slice edge gets stuck parallel to, but not on, the actual slice edge.
        # Perhaps, after the optimization stops, we could sample the neigbourhood of the slice for better slice shapes. For example by trying
        # to move each slice edge parallel to itself and checking the score to see if it better (maybe after running a couple of extra gradient descent steps).
        # Or, after optimization, we could jitter the solution's vertices a bit and run the optimization again. Then compare the scores of a couple of final
        # slice contours obtained that way.

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
        sample_weight = distance_v1_v2 / num_samples
        score = 0.0
        for i in range(num_samples):
            pos = v1 + i * exact_distance_between_samples * direction
            score += tools.sample_image(image, pos) * sample_weight
        return score
