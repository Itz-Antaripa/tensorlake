import unittest


@unittest.skip(
    "The test is triggered manually, it requires S3 credentials and a specific S3 bucket setup."
)
class TestS3BLOBStore(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
