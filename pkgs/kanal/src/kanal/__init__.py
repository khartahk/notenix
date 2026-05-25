"""kanal — notenix update-channel switcher."""

import gettext as _gettext
import os

# TEXTDOMAINDIR is set by wrapProgram in the Nix build.
# Falls back to the standard system path for non-Nix installs.
_localedir = os.environ.get("TEXTDOMAINDIR", "/usr/share/locale")

_gettext.bindtextdomain("kanal", _localedir)
_gettext.textdomain("kanal")

#: Translation function — import this everywhere: ``from kanal import _``
_ = _gettext.gettext
