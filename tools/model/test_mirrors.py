"""Donor extraction, fitting and reflection checks: python tools/model/test_mirrors.py."""
import unittest
import numpy as np
import mirrors as M


class MirrorGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = M.build()

    def test_extraction_contains_only_mirrors(self):
        for part, count in [('housing', 2797), ('glass', 112)]:
            with self.subTest(part=part):
                v, f, n = M.source(part)
                self.assertEqual(len(f), count)
                self.assertTrue((v.min(0) > [.30, .75, .75]).all())
                self.assertTrue((v.max(0) < [.55, 1.00, .90]).all())
                with np.load(M.ASSETS / f'mirror_{part}_source.npz') as data:
                    self.assertEqual(data['UV'].shape, (len(v), 2))
                    self.assertEqual(data['FIT'].shape, (len(v),))
                    self.assertTrue(np.isfinite(data['UV']).all())

    def test_valid_geometry_and_normals(self):
        for name, (v, f, n) in self.parts.items():
            with self.subTest(part=name):
                self.assertTrue(np.isfinite(v).all() and np.isfinite(n).all())
                np.testing.assert_allclose(np.linalg.norm(n, axis=1), 1, atol=1e-7)
                self.assertGreaterEqual(f.min(), 0)
                self.assertLess(f.max(), len(v))
                face = np.cross(v[f[:, 1]]-v[f[:, 0]], v[f[:, 2]]-v[f[:, 0]])
                self.assertGreater(np.linalg.norm(face, axis=1).min(), 1e-9)
                self.assertTrue((np.einsum('ij,ij->i', face, n[f].mean(1)) > 0).all())

    def test_head_and_glass_keep_source_shape(self):
        anchor, target, rotation = M.root_transform()
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-10)
        self.assertAlmostEqual(np.linalg.det(rotation), 1)
        for part, key in [('housing', 'mirror_L'), ('glass', 'mirror_glass_L')]:
            with np.load(M.ASSETS / f'mirror_{part}_source.npz') as data:
                fixed = ~data['FIT']
                expected = (data['V'][fixed]-anchor) @ rotation.T+target
                v, f, _ = self.parts[key]
                corners = v[f].reshape(-1, 3)
                np.testing.assert_allclose(corners[fixed], expected, atol=1e-10)
                self.assertEqual(f.shape, data['F'].shape)

    def test_mount_contacts_door(self):
        with np.load(M.ASSETS / 'mirror_housing_source.npz') as data:
            d = (data['V']-M.ROOT_POINT) @ M.ROOT_NORMAL
            contact = data['FIT'] & (abs(d) < .002)
        self.assertGreater(contact.sum(), 100)
        all_v, all_f, all_n = self.parts['mirror_L']
        corners = all_v[all_f].reshape(-1, 3)
        v = corners[contact]
        distance = M.B.flanks(*v.T)-M.B.DOOR_SEAL_OFFSET
        self.assertLess(distance.min(), 0)
        self.assertLess(abs(distance).max(), .003)
        from extract import sdf_normals
        normals = all_n[all_f].reshape(-1, 3)
        front = np.sum(sdf_normals(M.B.flanks, corners)*normals, axis=1) > .3
        with np.load(M.ASSETS / 'mirror_housing_source.npz') as data:
            front &= data['FIT']
        # Embedded front vertices turn into dark sawteeth after the AO bake.
        self.assertGreater(M.B.flanks(*corners[front].T).min(), .001)
        # The head and glass must stay outside the door surface.
        self.assertGreater(M.B.flanks(*self.parts['mirror_glass_L'][0].T).min(), .005)

    def test_shared_corners_for_continuous_ao(self):
        for name in ('mirror_L', 'mirror_glass_L'):
            v, f, _ = self.parts[name]
            # A corner-per-triangle mesh prevents the AO neighbour pass from
            # smoothing across faces, producing dark triangular patches.
            used = np.bincount(f.ravel(), minlength=len(v))
            self.assertGreater((used > 1).mean(), .75)
            self.assertLess(len(v), f.size*.6)

    def test_exact_reflection(self):
        for name in ('mirror', 'mirror_glass'):
            left, right = self.parts[name+'_L'], self.parts[name+'_R']
            np.testing.assert_array_equal(left[0]*[1, -1, 1], right[0])
            np.testing.assert_array_equal(left[1][:, [0, 2, 1]], right[1])
            np.testing.assert_array_equal(left[2]*[1, -1, 1], right[2])


if __name__ == '__main__':
    unittest.main()
