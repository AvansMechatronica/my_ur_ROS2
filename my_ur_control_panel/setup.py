from setuptools import find_packages, setup

package_name = 'my_ur_control_panel'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gerard',
    maintainer_email='ga.harkema@avans.nl',
    description='PyQt GUI for the UR ros2_control controllers topics and services',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'control_panel = my_ur_control_panel.control_panel:main'
        ],
    },
)
