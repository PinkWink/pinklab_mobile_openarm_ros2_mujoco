from pathlib import Path
from setuptools import setup

name = "warehouse_skills"
data = [
    ("share/ament_index/resource_index/packages", ["resource/" + name]),
    ("share/" + name, ["package.xml"]),
    ("share/" + name + "/config", [str(p) for p in sorted(Path("config").glob("*"))]),
]
setup(
    name=name,
    version="0.1.0",
    packages=[name],
    data_files=data,
    install_requires=["setuptools"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "pick_place_server = warehouse_skills.pick_place_server:main",
            "pick_place = warehouse_skills.pick_place_client:main",
        ]
    },
)
