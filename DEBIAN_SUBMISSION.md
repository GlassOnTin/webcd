# Debian Package Submission Guide for WebCD

This guide outlines the process for submitting WebCD to the official Debian repositories.

## Prerequisites

1. **Debian Developer Account** or find a sponsor
2. **GPG Key** registered with Debian
3. **Familiar with Debian Policy**: https://www.debian.org/doc/debian-policy/

## Step-by-Step Process

### 1. File an ITP (Intent to Package)

```bash
reportbug wnpp
```

Select "ITP" and provide:
- Package: webcd
- Version: 0.1.0
- Upstream Author: GlassOnTin <your-email>
- URL: https://github.com/GlassOnTin/webcd
- License: MIT
- Programming Lang: Python
- Description: Web-based CD player interface

### 2. Prepare the Package

```bash
# Install required tools
sudo apt install devscripts dh-python python3-all debhelper lintian git-buildpackage

# Clone and prepare
git clone https://github.com/GlassOnTin/webcd.git
cd webcd

# Create pristine upstream tarball
git archive --format=tar.gz --prefix=webcd-0.1.0/ -o ../webcd_0.1.0.orig.tar.gz HEAD

# Build the package
dpkg-buildpackage -us -uc

# Check with lintian
lintian -iIE --pedantic ../webcd_0.1.0-1_all.deb
```

### 3. Package Improvements Needed

Before submission, address these common requirements:

1. **debian/copyright**: Must be in DEP-5 format
2. **debian/control**:
   - Add Vcs-Git and Vcs-Browser fields
   - Ensure all dependencies are in Debian
   - Add autopkgtest support
3. **debian/rules**: Ensure it's minimal and uses dh
4. **debian/tests/**: Add autopkgtest suite

### 4. Upload to mentors.debian.net

1. Create account at https://mentors.debian.net/
2. Generate source package:
   ```bash
   dpkg-buildpackage -S -sa
   ```
3. Upload:
   ```bash
   dput mentors ../webcd_0.1.0-1_source.changes
   ```

### 5. Find a Sponsor

- Post to debian-mentors@lists.debian.org
- Include:
  - Link to mentors.debian.net package page
  - ITP bug number
  - Brief description of the package
  - Why it should be in Debian

### 6. Work with Your Sponsor

- Address all feedback promptly
- Make requested changes
- Re-upload to mentors as needed
- Sponsor will upload to Debian when ready

## Timeline

- Initial review: 1-2 weeks
- Addressing feedback: 1-4 weeks
- NEW queue (first upload): 2-8 weeks
- Total: 1-3 months typically

## Resources

- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Debian Developer's Reference](https://www.debian.org/doc/manuals/developers-reference/)
- [Debian Mentors FAQ](https://mentors.debian.net/intro-maintainers)
- [Debian Python Policy](https://www.debian.org/doc/packaging-manuals/python-policy/)

## Package Checklist

- [ ] ITP bug filed
- [ ] debian/copyright in DEP-5 format
- [ ] debian/watch file for upstream monitoring
- [ ] debian/upstream/metadata
- [ ] Lintian clean (no errors, minimal warnings)
- [ ] Autopkgtest suite
- [ ] Builds in clean chroot (pbuilder/sbuild)
- [ ] Works with Python 3.9+ (Debian stable)
- [ ] No embedded code copies
- [ ] Proper systemd integration
- [ ] Man page for executables