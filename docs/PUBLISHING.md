# Publishing to PyPI Guide

This guide explains how to publish the Web Research Agent to PyPI.

## Prerequisites

1. **PyPI Account**
   - Create account at https://pypi.org/account/register/
   - Verify your email address

2. **API Token**
   - Go to https://pypi.org/manage/account/
   - Scroll to "API tokens"
   - Create a new token with "Entire account" scope
   - Save the token securely (starts with `pypi-`)

3. **Install Build Tools**
   ```bash
   pip install --upgrade build twine
   ```

## Version Management

Before publishing, update the version number in these files:

1. `pyproject.toml` - line 7: `version = "X.Y.Z"`
2. `setup.py` - line 21: `version="X.Y.Z"`
3. `cli.py` - line 33: `VERSION = "X.Y.Z"`
4. `__init__.py` - line 23: `__version__ = "X.Y.Z"`
5. `CHANGELOG.md` - Add new version section

### Version Numbering (Semantic Versioning)

- **Major (X.0.0)**: Breaking changes
- **Minor (X.Y.0)**: New features, backward compatible
- **Patch (X.Y.Z)**: Bug fixes, backward compatible

Current version: **1.2.0**

## Pre-Publishing Checklist

- [ ] All tests pass
- [ ] Version updated in all files
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md reflects current features
- [ ] requirements.txt contains only necessary dependencies
- [ ] All changes committed to git
- [ ] Git tag created for version

## Build the Distribution

1. **Clean previous builds**:
   ```bash
   rm -rf dist/ build/ *.egg-info
   ```

2. **Build the package**:
   ```bash
   python -m build
   ```

   This creates:
   - `dist/web_research_agent-X.Y.Z.tar.gz` (source distribution)
   - `dist/web_research_agent-X.Y.Z-py3-none-any.whl` (wheel)

3. **Verify the build**:
   ```bash
   twine check dist/*
   ```

   Should show: "PASSED" for all files

## Test with TestPyPI (Optional but Recommended)

1. **Upload to TestPyPI**:
   ```bash
   twine upload --repository testpypi dist/*
   ```

   Enter your TestPyPI credentials when prompted.

2. **Test installation**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ web-research-agent
   ```

3. **Test the CLI**:
   ```bash
   webresearch
   ```

4. **Uninstall test version**:
   ```bash
   pip uninstall web-research-agent
   ```

## Publish to PyPI

1. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```

   Enter your PyPI API token when prompted:
   - Username: `__token__`
   - Password: Your API token (including `pypi-` prefix)

2. **Verify on PyPI**:
   - Visit https://pypi.org/project/web-research-agent/
   - Check version number
   - Verify README renders correctly
   - Check that all metadata is correct

## Post-Publishing Steps

1. **Create Git tag**:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

2. **Create GitHub Release**:
   - Go to GitHub repository
   - Click "Releases" → "Draft a new release"
   - Select the tag you just created
   - Title: `v1.2.0`
   - Copy release notes from CHANGELOG.md
   - Publish release

3. **Test installation from PyPI**:
   ```bash
   pip install --upgrade web-research-agent
   webresearch
   ```

4. **Announce the release** (optional):
   - Social media
   - Project website
   - Mailing list
   - Discord/Slack communities

## GitHub Actions Automation (If Configured)

If you have GitHub Actions set up for automatic publishing:

1. **Push to main branch**:
   ```bash
   git push origin main
   ```

2. **Create and push tag**:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

3. **GitHub Actions will automatically**:
   - Build the package
   - Run tests
   - Upload to PyPI (if configured with secrets)
   - Create GitHub release

## Troubleshooting

### "File already exists" error

This means the version was already published. You need to:
1. Increment the version number
2. Update all version files
3. Rebuild and upload

### README not rendering on PyPI

- Ensure `long_description_content_type="text/markdown"` in setup.py
- Check that README.md is valid Markdown
- Verify README.md is included in MANIFEST.in

### Import errors after installation

- Check that all modules are listed in `pyproject.toml`
- Verify `__init__.py` imports are correct
- Test in a fresh virtual environment

### Missing dependencies

- Ensure all dependencies are in requirements.txt
- Check that requirements.txt is included in MANIFEST.in
- Verify dependencies are listed in pyproject.toml

## Quick Reference

```bash
# Complete publishing workflow
rm -rf dist/ build/ *.egg-info
python -m build
twine check dist/*
twine upload dist/*
git tag v1.2.0
git push origin v1.2.0
```

## Using API Token in CI/CD

Store your PyPI API token as a secret:

1. **GitHub Actions**: 
   - Settings → Secrets → New repository secret
   - Name: `PYPI_API_TOKEN`
   - Value: Your token

2. **In workflow file** (`.github/workflows/publish.yml`):
   ```yaml
   - name: Publish to PyPI
     env:
       TWINE_USERNAME: __token__
       TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
     run: |
       python -m build
       twine upload dist/*
   ```

## Version History on PyPI

Current published versions can be viewed at:
https://pypi.org/project/web-research-agent/#history

## Support

For issues with publishing:
- PyPI Help: https://pypi.org/help/
- Twine docs: https://twine.readthedocs.io/
- Packaging guide: https://packaging.python.org/

## Checklist Summary

Before each release:

1. [ ] Update version in 4 files
2. [ ] Update CHANGELOG.md
3. [ ] Clean old builds
4. [ ] Build package
5. [ ] Check with twine
6. [ ] Upload to PyPI
7. [ ] Create git tag
8. [ ] Create GitHub release
9. [ ] Test installation
10. [ ] Announce release

---

**Last Updated**: 2025-01-10
**Current Version**: 1.2.0
**PyPI URL**: https://pypi.org/project/web-research-agent/