import unittest

from charm import Microsample
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(Microsample)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_pass(self):
        pass