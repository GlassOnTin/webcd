.PHONY: clean build install deb

VERSION := 1.0.0

clean:
	rm -rf build dist *.egg-info
	rm -rf debian/.debhelper debian/webcd debian/files debian/*.log debian/*.substvars
	rm -f ../webcd_*.deb ../webcd_*.changes ../webcd_*.dsc ../webcd_*.buildinfo

build:
	python3 setup.py build

install:
	python3 setup.py install --user

deb: clean
	dpkg-buildpackage -us -uc -b

deb-signed:
	dpkg-buildpackage -b

source-package:
	dpkg-buildpackage -S

test-install:
	sudo dpkg -i ../webcd_$(VERSION)-1_all.deb

test-remove:
	sudo apt remove webcd -y

test-purge:
	sudo apt purge webcd -y