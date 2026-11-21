import csv
import phonenumbers as pn
import vobject

from pathlib import Path

from .utility import vcard


class Service:
    def __init__(self, data_dir: Path, default_phone_number_region_code: str) -> None:
        self._contacts_path = data_dir / "contacts.tsv"
        self._default_phone_number_region_code = default_phone_number_region_code

    def find_contact_name(self, number: pn.PhoneNumber) -> str:
        formatted = pn.format_number(number, pn.PhoneNumberFormat.E164)

        try:
            with open(self._contacts_path, encoding="utf-8", newline="") as source:
                reader = csv.reader(source, delimiter="\t")
                for row in reader:
                    if row and formatted in row[1:]:
                        return row[0]
        except FileNotFoundError:
            pass

        return ""

    def replace_contacts_with_vcard(self, path: Path) -> None:
        with (
            open(path, encoding="utf-8-sig") as source,
            open(self._contacts_path, "w", encoding="utf-8", newline="") as output,
        ):
            writer = csv.writer(output, delimiter="\t")

            for contact in vobject.readComponents(source):
                if contact.name != "VCARD":
                    continue

                full_name = vcard.get_contact_full_name(contact)
                if not full_name:
                    continue

                numbers = vcard.get_contact_phone_numbers(
                    contact, self._default_phone_number_region_code
                )
                if numbers:
                    writer.writerow([full_name, *numbers])
