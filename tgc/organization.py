"""Organization profile utilities for the controller."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

DEFAULT_PROFILE_PATH = Path("organization_profile.json")
DEFAULT_REFERENCE_PATH = Path("docs/organization_reference.md")
PLACEHOLDER_NAME = "Your Business Name"
PLACEHOLDER_SHORT_CODE = "XXX"


@dataclass
class OrganizationProfile:
    """Store basic organization metadata and helper formatting."""

    name: str = PLACEHOLDER_NAME
    short_code: str = PLACEHOLDER_SHORT_CODE
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    notes: str = ""

    @classmethod
    def load(cls, path: Path = DEFAULT_PROFILE_PATH) -> "OrganizationProfile":
        profile = cls()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            for key, value in data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        profile.short_code = cls.normalize_short_code(profile.short_code)
        if not profile.name:
            profile.name = PLACEHOLDER_NAME
        return profile

    def save(self, path: Path = DEFAULT_PROFILE_PATH) -> None:
        data = self.to_dict()
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "short_code": self.short_code,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "notes": self.notes,
        }

    @staticmethod
    def normalize_short_code(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", value or "")
        return cleaned.upper() if cleaned else PLACEHOLDER_SHORT_CODE

    @staticmethod
    def derive_short_code(name: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", name or "")
        if not tokens:
            return PLACEHOLDER_SHORT_CODE
        letters = "".join(token[0] for token in tokens[:3]).upper()
        if letters:
            return letters
        alnum = re.sub(r"[^A-Za-z0-9]", "", name)
        return alnum[:3].upper() or PLACEHOLDER_SHORT_CODE

    def has_custom_name(self) -> bool:
        return bool(self.name and self.name != PLACEHOLDER_NAME)

    def has_custom_short_code(self) -> bool:
        return bool(self.short_code and self.short_code != PLACEHOLDER_SHORT_CODE)

    def display_name(self) -> str:
        return self.name if self.has_custom_name() else "Organization"

    def sku_example(self, sequence: int = 1) -> str:
        prefix = self.short_code if self.has_custom_short_code() else "[xxx]"
        return f"{prefix}-{sequence:03d}"

    def summary_lines(self) -> List[str]:
        return [
            f"Business name: {self.name if self.has_custom_name() else 'Set via `python app.py --init-org`'}",
            f"Short code: {self.short_code if self.has_custom_short_code() else 'XXX (placeholder)'}",
            f"SKU example: {self.sku_example()}",
            f"Email: {self.email or 'Not provided'}",
            f"Phone: {self.phone or 'Not provided'}",
            f"Website: {self.website or 'Not provided'}",
            f"Address: {self.address or 'Not provided'}",
        ]

    def reference_markdown(self) -> str:
        lines: List[str] = ["# Organization Reference", ""]
        lines.append("This page is generated from `organization_profile.json`. Update it via `python app.py --init-org` or by editing the file directly.")
        lines.append("")
        lines.extend(
            [
                f"- **Business name:** {self.name if self.has_custom_name() else 'Pending setup'}",
                f"- **Short code:** {self.short_code if self.has_custom_short_code() else 'XXX (placeholder)'}",
                f"- **SKU example:** `{self.sku_example()}`",
                f"- **Primary email:** {self.email or 'Pending setup'}",
                f"- **Phone:** {self.phone or 'Pending setup'}",
                f"- **Website:** {self.website or 'Pending setup'}",
                f"- **Address:** {self.address or 'Pending setup'}",
            ]
        )
        if self.notes:
            lines.append(f"- **Notes:** {self.notes}")
        lines.append("")
        lines.append("> Generated for quick reference during audits and adapter setup.")
        return "\n".join(lines).strip() + "\n"

    def ensure_reference_page(self, path: Path = DEFAULT_REFERENCE_PATH) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.reference_markdown(), encoding="utf-8")

    def write_reference_page(self, path: Path = DEFAULT_REFERENCE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.reference_markdown(), encoding="utf-8")


def configure_profile_interactive(
    profile_path: Path = DEFAULT_PROFILE_PATH,
    reference_path: Path = DEFAULT_REFERENCE_PATH,
) -> OrganizationProfile:
    """Prompt for organization details and persist them."""

    profile = OrganizationProfile.load(profile_path)
    print("Organization setup — press Enter to keep the current value.")

    profile.name = _prompt(
        "Business name",
        profile.name if profile.has_custom_name() else "",
        fallback=profile.name,
    )

    short_code_default = profile.short_code if profile.has_custom_short_code() else ""
    short_code_input = _prompt(
        "Preferred short code (used for IDs/SKUs)",
        short_code_default,
        fallback=short_code_default,
    )
    if not short_code_input and profile.name:
        short_code_input = OrganizationProfile.derive_short_code(profile.name)
    profile.short_code = OrganizationProfile.normalize_short_code(short_code_input or profile.short_code)

    profile.email = _prompt("Primary email", profile.email, fallback=profile.email)
    profile.phone = _prompt("Phone", profile.phone, fallback=profile.phone)
    profile.website = _prompt("Website", profile.website, fallback=profile.website)
    profile.address = _prompt("Address", profile.address, fallback=profile.address)
    profile.notes = _prompt("Notes", profile.notes, fallback=profile.notes)

    profile.save(profile_path)
    profile.write_reference_page(reference_path)

    print("\nSaved organization profile:")
    for line in profile.summary_lines():
        print(f"- {line}")
    print(f"\nReference page updated at: {reference_path}")
    return profile


def _prompt(message: str, default: str, fallback: str = "") -> str:
    prompt = f"{message}" + (f" [{default}]" if default else "") + ": "
    value = input(prompt).strip()
    if value:
        return value
    return fallback


def organization_status_lines(profile: OrganizationProfile) -> Iterable[str]:
    yield from profile.summary_lines()
    if profile.has_custom_short_code():
        yield "SKU format ready for production IDs."
    else:
        yield "SKU format is still using the placeholder prefix `[xxx]`."

