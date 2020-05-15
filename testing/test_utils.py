import unittest

from toscatranslator.providers.common.python_sources import transform_units

KIBS = '230 KiB'
GIBS = '230 GiB'
class TestUtills(unittest.TestCase):
    def test_transform_units(self):
        # from bytes to bytes
        self.assertEqual(transform_units('230 KB', 'MB'), '0.23 MB')
        self.assertEqual(transform_units('230 MB', 'KB'), '230000.0 KB')
        self.assertEqual(transform_units('230 KB', 'GB'), '0.00023 GB')
        self.assertEqual(transform_units('230 GB', 'KB'), '230000000.0 KB')
        # from bibytes to bibytes
        self.assertEqual(transform_units('230 MiB', 'KiB'), '235520.0 KiB')
        self.assertEqual(transform_units(KIBS, 'MiB'), '0.224609375 MiB')
        self.assertEqual(transform_units(KIBS, 'GiB'), '0.0002193450927734375 GiB')
        self.assertEqual(transform_units(GIBS, 'KiB'), '241172480.0 KiB')
        # from bytes to bibytes
        self.assertEqual(transform_units('230 MB', 'KiB'), '224609.375 KiB')
        self.assertEqual(transform_units('230 KB', 'MiB'), '0.2193450927734375 MiB')
        self.assertEqual(transform_units('230 KB', 'GiB'), '0.00021420419216156006 GiB')
        self.assertEqual(transform_units('230 GB', 'KiB'), '224609375.0 KiB')
        # from bibytes to bytes
        self.assertEqual(transform_units('230 MiB', 'KB'), '241172.48 KB')
        self.assertEqual(transform_units(KIBS, 'MB'), '0.23552 MB')
        self.assertEqual(transform_units(KIBS, 'GB'), '0.00023552000000000002 GB')
        self.assertEqual(transform_units(GIBS, 'KB'), '246960619.52 KB')
        # equals
        self.assertEqual(transform_units('230 GB', 'GB'), '230.0 GB')
        self.assertEqual(transform_units(KIBS, 'KiB'), '230.0 KiB')
        self.assertEqual(transform_units('230 KB', 'KiB'), '224.609375 KiB')
        self.assertEqual(transform_units('230 GB', 'GiB'), '214.20419216156006 GiB')
        self.assertEqual(transform_units(KIBS, 'KB'), '235.52 KB')
        self.assertEqual(transform_units(GIBS, 'GB'), '246.96061952000002 GB')
        #other
        self.assertEqual(transform_units(KIBS, 'KB', is_without_b=True), '235.52 K')
        self.assertEqual(transform_units(KIBS, is_without_b=True), '230 KI')
        self.assertEqual(transform_units(KIBS, 'KiB', is_without_b=True), '230.0 Ki')
        self.assertEqual(transform_units(KIBS, 'KB', is_only_numb=True), '235.52 ')
        self.assertEqual(transform_units(KIBS, 'KiB', is_only_numb=True,is_without_b=True), '230.0 ')

