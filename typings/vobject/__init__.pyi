from collections.abc import Iterator
from typing import TextIO

from vobject.base import Component

def readComponents(
    streamOrString: TextIO | str,
    validate: bool = False,
    transform: bool = True,
    ignoreUnreadable: bool = False,
    allowQP: bool = False,
) -> Iterator[Component]: ...
