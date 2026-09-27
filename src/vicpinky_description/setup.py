from pathlib import Path
from setuptools import setup
name = 'vicpinky_description'
data = [('share/ament_index/resource_index/packages', ['resource/' + name]),
        ('share/' + name, ['package.xml'] + [str(p) for p in Path('.').glob('*.md')] + [str(p) for p in Path('.').glob('LICENSE*')])]
for folder in ('urdf', 'meshes'):
    files = [p for p in Path(folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for directory in sorted({p.parent for p in files}):
        data.append(('share/' + name + '/' + str(directory), [str(p) for p in sorted(files) if p.parent == directory]))
setup(name=name, version='0.1.0', packages=[name], data_files=data,
      install_requires=['setuptools'], zip_safe=False,
      entry_points={'console_scripts': []})
