#!/usr/bin/env python

from setuptools import setup, find_packages
import distutils
VERSION = '0.1.11'

ENTRY_POINTS = {
    'orange3.addon': (
        'datafusion = orangecontrib.datafusion',
    ),
    # Entry point used to specify packages containing tutorials accessible
    # from welcome screen. Tutorials are saved Orange Workflows (.ows files).
    'orange.widgets.tutorials': (
        # Syntax: any_text = path.to.package.containing.tutorials
        'fusiontutorials = orangecontrib.datafusion.tutorials',
    ),

    # Entry point used to specify packages containing widgets.
    'orange.widgets': (
        # Syntax: category name = path.to.package.containing.widgets
        # Widget category specification can be seen in
        #    orangecontrib/datafusion/widgets/__init__.py
        'Data Fusion = orangecontrib.datafusion.widgets',
    ),
    
    # Register widget help
    "orange.canvas.help": (
        'html-index = orangecontrib.datafusion.widgets:WIDGET_HELP_PATH',),
}

if __name__ == '__main__':
    setup(
        name="Orange3-DataFusion",
        description="Orange DataFusion add-on.",
        version=VERSION,
        author='Bioinformatics Laboratory, FRI UL',
        author_email='contact@orange.biolab.si',
        url='https://github.com/biolab/orange3-datafusion',
        keywords=(
            'data mining',
            'orange3 add-on',
        ),
        packages=find_packages(),
        package_data={
            "orangecontrib.datafusion": ["datasets/*.csv"],
            "orangecontrib.datafusion.widgets": ["icons/*.svg"],
            "orangecontrib.datafusion.tutorials": ["*.ows"],
        },
        install_requires=[
            'Orange3',
            'scikit-fusion',
        ],
        entry_points=ENTRY_POINTS,
        namespace_packages=['orangecontrib'],
        zip_safe=False,
    )
