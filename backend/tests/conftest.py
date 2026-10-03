"""Keep module-level coordinators away from the running application's cache."""
import os
from tempfile import TemporaryDirectory
from pathlib import Path

_test_storage = TemporaryDirectory(prefix="smp-test-storage-")
os.environ["SMP_DATA_DIR"] = _test_storage.name
os.environ["SMP_DB_PATH"] = str(Path(_test_storage.name) / "bootstrap.sqlite")
os.environ["SMP_PRIVATE_DIR"] = str(Path(_test_storage.name) / "test-config")
