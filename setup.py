from setuptools import setup, find_packages

setup(
    name='webcd',
    version='1.0.0',
    description='Web-based CD player with streaming support',
    author='GlassOnTin',
    author_email='glassontin@users.noreply.github.com',
    url='https://github.com/GlassOnTin/webcd',
    py_modules=['app'],
    install_requires=[
        'flask>=3.1.0',
        'flask-cors>=5.0.0',
        'python-dotenv>=1.0.1',
        'musicbrainzngs>=0.7.1',
        'requests>=2.32.3',
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)