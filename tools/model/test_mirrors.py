"""Mirror rebuild invariants: python tools/model/test_mirrors.py."""
import unittest
import numpy as np
import body as B
import mirrors as M


def inside(mesh, points):
    """Solid-angle containment; no ray-casting/rtree dependency needed."""
    vertices, faces, _ = mesh
    triangles = vertices[faces]
    result = []
    for chunk in np.array_split(points, max(1, len(points) // 24)):
        a, b, c = [triangles[None, :, i, :] - chunk[:, None, :] for i in range(3)]
        la, lb, lc = [np.linalg.norm(v, axis=-1) for v in (a, b, c)]
        det = np.einsum('pfi,pfi->pf', a, np.cross(b, c))
        den = (la*lb*lc + np.einsum('pfi,pfi->pf', a, b)*lc
               + np.einsum('pfi,pfi->pf', b, c)*la
               + np.einsum('pfi,pfi->pf', c, a)*lb)
        winding = np.sum(2*np.arctan2(det, den), axis=1)
        result.extend(abs(winding) > 2*np.pi)
    return np.asarray(result)


class MirrorGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = dict(head=M.housing(), plate=M.sail_plate(),
                         base=M.pedestal(), shoe=M.shoe(), glass=M.glass())

    def test_closed_outward_solids(self):
        for name, (v, f, n) in self.parts.items():
            with self.subTest(part=name):
                self.assertTrue(np.isfinite(v).all() and np.isfinite(n).all())
                np.testing.assert_allclose(np.linalg.norm(n, axis=1), 1)
                edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]],
                                                f[:, [2, 0]]]), axis=1)
                _, counts = np.unique(edges, axis=0, return_counts=True)
                self.assertTrue((counts == 2).all())
                a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
                self.assertGreater(np.linalg.norm(np.cross(b-a, c-a), axis=1).min(), 1e-11)
                self.assertGreater(np.einsum('ij,ij->i', a, np.cross(b, c)).sum(), 0)

    def test_connected_support(self):
        # Separate moulded pieces must overlap structurally, even at the narrow
        # visible joint. Sample both directions so a small part inside a larger
        # one cannot produce a false negative.
        for a, b in [('head', 'base'), ('head', 'shoe'), ('base', 'shoe'), ('base', 'plate')]:
            with self.subTest(joint=(a, b)):
                overlap = (inside(self.parts[a], self.parts[b][0][::16]).any()
                           or inside(self.parts[b], self.parts[a][0][::16]).any())
                self.assertTrue(overlap)

    def test_door_contact_and_glass_clearance(self):
        self.assertLess(B.flanks(*self.parts['plate'][0].T).min(), -.003)
        self.assertGreater(B.flanks(*self.parts['glass'][0].T).min(), .004)

    def test_exact_reflection(self):
        parts = M.build()
        for name in ('mirror', 'mirror_glass'):
            left, right = parts[name+'_L'], parts[name+'_R']
            np.testing.assert_array_equal(left[0]*[1, -1, 1], right[0])
            np.testing.assert_array_equal(left[1][:, [0, 2, 1]], right[1])
            np.testing.assert_array_equal(left[2]*[1, -1, 1], right[2])


if __name__ == '__main__':
    unittest.main()
