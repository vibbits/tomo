import numpy as np
import math
import tools
import cv2

class ContourFinder:

    def __init__(self):
        self.h_for_gradient_approximation = 1.0
        self.max_iterations = 50
        self.gradient_step_size = 5e-3
        self.edge_sample_distance = 50.0

    def set_optimization_parameters(self, h_for_gradient_approximation, max_iterations, gradient_step_size, edge_sample_distance):
        # :param h_for_gradient_approximation: used for numeric gradient approximation: gradient = (f(x+h)-f(x)) / h
        # :param max_iterations: the maximum number of iterations of gradient descent that will be performed to improve the slice contour
        # :param gradient_step_size: the distance to move along the gradient during each iteration of gradient descent
        self.h_for_gradient_approximation = h_for_gradient_approximation
        self.max_iterations = max_iterations
        self.gradient_step_size = gradient_step_size
        self.edge_sample_distance = edge_sample_distance

    def optimize_contour(self, image, initial_contour):
        """
        :param image: preprocessed overview image with the ribbons of slices
        :param initial_contour: list of (x,y) vertex coordinates
        :return: optimized contour    # FIXME: what if there is not really a contour in that neighborhood of the image? return score too, so we can compare it to the score of the initial contour somehow?
        """
        iteration = 0
        current_contour = initial_contour  # CHECKME: deep copy needed?

        current_contour_vector = self.contour_to_vector(current_contour)
        print('initial contour={} score={}'.format(current_contour_vector, self.calculate_contour_score(image, current_contour_vector)))

        while iteration < self.max_iterations:  # FIXME: and gradient (or score?) is still changing
            gradient_vector = self._calculate_gradient(image, current_contour_vector)
            current_contour_vector = current_contour_vector + self.gradient_step_size * gradient_vector   # we are looking for a maximum of the score, so we move along the positive gradient
            # print('Contour update: gradient step size={} gradient vector={} update={}'.format(self.gradient_step_size, gradient_vector, self.gradient_step_size * gradient_vector))
            # print('iteration {} score={}'.format(iteration, self.calculate_contour_score(image, current_contour_vector)))
            # note: the gradient points towards higher values of the function
            iteration += 1

        return self.vector_to_contour(current_contour_vector)

    def preprocess_image(self, image_path):
        # For now just read the result of manual preprocessing in Fiji...
        # TODO: IMPLEMENT: e.g. blur image, remove dark specks, etc.
        # http://opencvexamples.blogspot.com/2013/10/edge-detection-using-laplacian-operator.html

        if True:
            # Read preprocessed version of "20x_lens\bisstitched-0.tif" where contrast was enhanced, edges were amplified and then blurred to make gradient descent work better.
            preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40.tif'  # WORKS
            preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius20-gaussianblur20pix.tif' # WORKS BETTER?
            print('Should preprocess {} but instead we will just read the result {}'.format(image_path, preprocessed_path))

            return tools.read_image_as_grayscale(preprocessed_path)
        else:
            # Here we try to obtain a similar result using OpenCV.
            # It doesn't work yet (almost black result). Parameter values are probably not correct. We also did not do contrast enhancement first yet either.
            image_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\oneslice_16bit.tif'

            raw_img = tools.read_image_as_grayscale(image_path, cv2.IMREAD_GRAYSCALE + cv2.IMREAD_ANYDEPTH)  # IMREAD_ANYDEPTH to preserve as 16 bit
            print('Raw: shape={} dtype={} min={} max={}'.format(raw_img.shape, raw_img.dtype, np.min(raw_img), np.max(raw_img)))
            tools.display(raw_img, "Raw")

            kernel_size = (31, 31)  # must be odd
            sigma_x, sigma_y = 0, 0   # 0 means calculate sigma from the kernel size
            img = cv2.GaussianBlur(raw_img, kernel_size, sigma_x, sigma_y)
            print('Img Gauss: shape={} dtype={} min={} max={}'.format(img.shape, img.dtype, np.min(img), np.max(img)))
            tools.display(img, "Gaussian")

            ddepth = cv2.CV_16U  #cv2.CV_8U
            kernel_size = 31
            result = cv2.Laplacian(img, ddepth, kernel_size) * 100 #* 20  # TEST TEST TOO DARK OTHERWISE
            print('Result Laplacian: shape={} dtype={} min={} max={}'.format(result.shape, result.dtype, np.min(result), np.max(result)))
            tools.display(result, "Laplacian (of Gaussian)")

            return result

            # Laplacian(gray, dst, CV_16S, 3, 1, 0, BORDER_DEFAULT);
            # convertScaleAbs(dst, abs_dst);
            # imshow("result", abs_dst);

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
        # IMPROVEME
        # This definition of score is not perfect: the algorithm tends to make the edges a bit too long:
        # the fact that this way less 'blackness' per pixel is collected, is compensated by the longer edges.
        # Maybe we ought to use some space-scale concept: the original edges get blurred relatively heavily to be able
        # to attract far away contour approximations. Then maybe after a couple of optimization iterations, when the contour is likely much closer
        # to its correct location, we switch to a less heavily blurred image. Due to the Gaussian intensity profile of the blurred edges,
        # a new equilibrium (closer to the true edge center) exists where the contour does not gain so much anymore from being longer
        # but passing through less dark pixels, and instead will move closer to the edge center again?
        # Or can we define a different score that does not have this undesirable effect of preferring too long edges?

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
