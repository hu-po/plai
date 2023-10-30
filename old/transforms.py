import numpy as np
import unittest

def translation_matrix(tx, ty, tz):
    return np.array([[1, 0, 0, tx],
                     [0, 1, 0, ty],
                     [0, 0, 1, tz],
                     [0, 0, 0, 1]])

def rotation_matrix_x(theta):
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[1, 0,  0, 0],
                     [0, c, -s, 0],
                     [0, s,  c, 0],
                     [0, 0,  0, 1]])

def rotation_matrix_y(theta):
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[ c, 0, s, 0],
                     [ 0, 1, 0, 0],
                     [-s, 0, c, 0],
                     [ 0, 0, 0, 1]])

def rotation_matrix_z(theta):
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[c, -s, 0, 0],
                     [s,  c, 0, 0],
                     [0,  0, 1, 0],
                     [0,  0, 0, 1]])

def rotation_matrix_to_quaternion(R):
    qw = np.sqrt(1 + R[0,0] + R[1,1] + R[2,2]) / 2
    qx = (R[2,1] - R[1,2]) / (4 * qw)
    qy = (R[0,2] - R[2,0]) / (4 * qw)
    qz = (R[1,0] - R[0,1]) / (4 * qw)
    return np.array([qw, qx, qy, qz])

def quaternion_to_rotation_matrix(q):
    qw, qx, qy, qz = q
    R = np.array([
        [1 - 2*qy**2 - 2*qz**2, 2*qx*qy - 2*qz*qw, 2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw, 1 - 2*qx**2 - 2*qz**2, 2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw, 2*qy*qz + 2*qx*qw, 1 - 2*qx**2 - 2*qy**2]
    ])
    return R

class TestTransforms(unittest.TestCase):
    def test_translation_matrix(self):
        self.assertTrue(np.array_equal(translation_matrix(1, 2, 3), np.array([[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1]])))

    def test_rotation_matrix_x(self):
        self.assertTrue(np.allclose(rotation_matrix_x(np.pi/2), np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])))

    def test_rotation_matrix_y(self):
        self.assertTrue(np.allclose(rotation_matrix_y(np.pi/2), np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]])))

    def test_rotation_matrix_z(self):
        self.assertTrue(np.allclose(rotation_matrix_z(np.pi/2), np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])))

    def test_rotation_matrix_to_quaternion(self):
        R = rotation_matrix_z(np.pi/2)
        self.assertTrue(np.allclose(rotation_matrix_to_quaternion(R), np.array([0.70710678, 0, 0, 0.70710678])))

    def test_quaternion_to_rotation_matrix(self):
        q = np.array([0.70710678, 0, 0, 0.70710678])
        self.assertTrue(np.allclose(quaternion_to_rotation_matrix(q), rotation_matrix_z(np.pi/2)[:3,:3]))

if __name__ == "__main__":
    unittest.main()