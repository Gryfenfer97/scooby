import re
import subprocess
import sys

from bs4 import BeautifulSoup
import numpy
import pytest

import scooby


def test_report():
    report = scooby.Report()
    text = str(report)
    assert len(text) > 0
    assert len(report.packages) > 0
    for pkg, vers in report.packages.items():
        assert isinstance(pkg, str)
        assert isinstance(vers, str)
    report = scooby.Report(core='numpy')
    assert 'numpy' in report.packages
    html = report._repr_html_()
    assert len(html) > 0
    # Same as what is printed in Travis build log
    report = scooby.Report(additional=['pytest', 'foo'])
    report = scooby.Report(
        additional=[
            'foo',
        ]
    )
    report = scooby.Report(
        additional=[
            pytest,
        ]
    )
    report = scooby.Report(additional=pytest)
    report = scooby.Report(additional=['collections', 'foo', 'aaa'], sort=True)


def test_dict():
    report = scooby.Report(['no_version', 'does_not_exist'])
    for key, value in report.to_dict().items():
        if key != 'MKL':
            assert key in report.__repr__()
        assert value[:10] in report.__repr__()


def test_inheritence_example():
    class Report(scooby.Report):
        def __init__(self, additional=None, ncol=3, text_width=80, sort=False):
            """Initiate a scooby.Report instance."""

            # Mandatory packages.
            core = ['psutil', 'mkl', 'numpy', 'scooby']

            # Optional packages.
            optional = [
                'your_optional_packages',
                'e.g.',
                'matplotlib',
                'foo',
            ]

            scooby.Report.__init__(
                self,
                additional=additional,
                core=core,
                optional=optional,
                ncol=ncol,
                text_width=text_width,
                sort=sort,
            )

    report = Report(['pytest'])
    assert 'psutil' in report.packages
    assert 'mkl' in report.packages
    assert 'numpy' in report.packages


def test_ipy():
    scooby.in_ipykernel()


def test_get_version():
    name, version = scooby.get_version(numpy)
    assert version == numpy.__version__
    assert name == "numpy"
    name, version = scooby.get_version("no_version")
    assert version == scooby.report.VERSION_NOT_FOUND
    assert name == "no_version"
    name, version = scooby.get_version("does_not_exist")
    assert version == scooby.report.MODULE_NOT_FOUND
    assert name == "does_not_exist"


def test_plain_vs_html():
    report = scooby.Report()
    text_html = BeautifulSoup(report._repr_html_()).get_text()
    text_plain = report.__repr__()

    text_plain = " ".join(re.findall("[a-zA-Z1-9]+", text_plain))
    text_html = " ".join(re.findall("[a-zA-Z1-9]+", text_html))

    # Plain text currently starts with `Date :`;
    # we should remove that, or add it to the html version too.
    assert text_html[20:] == text_plain[25:]


def test_extra_meta():
    report = scooby.Report(extra_meta=("key", "value"))
    assert "key : value" in report.__repr__()
    report = scooby.Report(extra_meta=(("key", "value"),))
    assert "key : value" in report.__repr__()
    report = scooby.Report(extra_meta=(("key", "value"), ("another", "one")))
    assert "key : value" in report.__repr__()
    assert "another : one" in report.__repr__()
    with pytest.raises(TypeError):
        report = scooby.Report(extra_meta=(("key", "value"), "foo"))
    with pytest.raises(TypeError):
        report = scooby.Report(extra_meta="foo")
    with pytest.raises(TypeError):
        report = scooby.Report(extra_meta="for")


@pytest.mark.skipif(sys.version_info.major < 3, reason="Tracking not supported on Python 2.")
def test_tracking():
    scooby.track_imports()
    from scipy.constants import mu_0  # noqa ; a float value

    report = scooby.TrackedReport()
    scooby.untrack_imports()
    import no_version  # noqa

    assert "numpy" in report.packages
    assert "scipy" in report.packages
    assert "no_version" not in report.packages
    assert "pytest" not in report.packages
    assert "mu_0" not in report.packages


def test_version_compare():
    assert scooby.meets_version('2', '1')
    assert not scooby.meets_version('1', '2')

    assert scooby.meets_version('1', '1')
    assert scooby.meets_version('0.1', '0.1')
    assert scooby.meets_version('0.1.0', '0.1.0')

    assert scooby.meets_version('1.0', '0.9')
    assert not scooby.meets_version('0.9', '1.0')

    assert scooby.meets_version('0.2.5', '0.1.8')
    assert not scooby.meets_version('0.1.8', '0.2.5')

    assert not scooby.meets_version('0.25.1', '0.25.2')
    assert scooby.meets_version('0.26.0', '0.25.2')
    assert scooby.meets_version('0.25.2', '0.25.2')

    assert not scooby.meets_version('0.25.2', '0.26')

    assert scooby.meets_version('0.28.0dev0', '0.25.2')

    with pytest.raises(ValueError):
        scooby.meets_version('0.25.2.0', '0.26')


def test_import_os_error():
    # pyvips requires libvips, etc., to be installed
    # We don't have this on CI, so this should throw an error on import
    # Make sure scooby can handle it.
    with pytest.raises(OSError):
        import pyvips  # noqa
    assert scooby.Report(['pyvips'])


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason="Not Linux.")
def test_import_time():
    # Relevant for packages which provide a CLI:
    # How long does it take to import?
    cmd = ["time", "-f", "%U", "python", "-c", "import scooby"]
    # Run it twice, just in case.
    subprocess.run(cmd)
    subprocess.run(cmd)
    # Capture it
    out = subprocess.run(cmd, capture_output=True)

    # Currently we check t < 0.15 s.
    assert float(out.stderr.decode("utf-8")[:-1]) < 0.15


def test_add():
    a = scooby.Report(['numpy', 'scipy'], optional=[])
    b = scooby.Report(['psutil'], optional=[])
    both = a + b
    print('yo')
    print(['numpy', 'scipy', 'psutil'] in both)
    assert ['numpy', 'scipy', 'psutil'] in both
    assert ['numpy', 'scipy'] not in b
    assert 'psutil' not in a
