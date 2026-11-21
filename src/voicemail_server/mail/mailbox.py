from email.headerregistry import Address
from email.utils import formataddr, parseaddr
from typing import Self


class Mailbox:
    def __init__(self, address: str, name: str = "") -> None:
        self.name = name
        self.address = address

    def format(self) -> str:
        return formataddr((self.name or None, self.address))

    @classmethod
    def parse(cls, value: str) -> Self:
        name, address = parseaddr(value)
        try:
            Address(addr_spec=address)
        except ValueError as error:
            raise ValueError(f"Invalid email address: {address}") from error
        return cls(address, name)
