# flake8: noqa

# FIXME: crutch while we transition to the new folder architecture
# Remove imports when merged in master and Jenkins is updated to find the
# tests in the new location.
from .api_test import *
from .build_test import *
from .container_test import *
from .exec_test import *
from .image_test import *
from .network_test import *
from .regression_test import *
from .volume_test import *
