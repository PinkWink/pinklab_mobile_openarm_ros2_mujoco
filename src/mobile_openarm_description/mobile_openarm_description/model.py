from pathlib import Path
from ament_index_python.packages import get_package_share_directory
import xacro


def expand_urdf(mappings=None):
    path = (
        Path(get_package_share_directory("mobile_openarm_description"))
        / "urdf/mobile_openarm.urdf.xacro"
    )
    options = {str(k): str(v) for k, v in (mappings or {}).items()}
    options["ros2_control"] = "false"
    return xacro.process_file(str(path), mappings=options).toxml()


def resolve_mesh(uri):
    if uri.startswith("package://"):
        package, relative = uri[10:].split("/", 1)
        return Path(get_package_share_directory(package)) / relative
    raise ValueError(f"Expected package mesh URI: {uri}")
