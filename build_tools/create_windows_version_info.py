from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VERSION_FILE = PROJECT_ROOT / "src" / "open_fish_reader" / "version.py"

OUTPUT_FILE = PROJECT_ROOT / "build_tools" / "windows_version_info.txt"


def read_version_constants(
    path: Path,
) -> dict[str, object]:
    tree = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )

    values: dict[str, object] = {}

    for node in tree.body:
        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        if len(node.targets) != 1:
            continue

        target = node.targets[0]

        if not isinstance(
            target,
            ast.Name,
        ):
            continue

        try:
            value = ast.literal_eval(node.value)
        except (
            ValueError,
            TypeError,
        ):
            continue

        values[target.id] = value

    return values


def required_text(
    values: dict[str, object],
    name: str,
) -> str:
    value = values.get(name)

    if not isinstance(value, str):
        raise TypeError(
            f"La constante {name} est absente ou n'est pas une chaîne dans {VERSION_FILE}."
        )

    return value


def main() -> None:
    values = read_version_constants(VERSION_FILE)

    app_name = required_text(
        values,
        "APP_NAME",
    )
    app_version = required_text(
        values,
        "APP_VERSION",
    )
    organization = required_text(
        values,
        "ORGANIZATION_NAME",
    )
    description = required_text(
        values,
        "APP_DESCRIPTION",
    )
    copyright_text = required_text(
        values,
        "COPYRIGHT",
    )

    version_numbers = [
        int(value)
        for value in re.findall(
            r"\d+",
            app_version,
        )[:4]
    ]

    version_numbers.extend([0] * (4 - len(version_numbers)))

    version_values = ", ".join(str(value) for value in version_numbers)

    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_values}),
    prodvers=({version_values}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040C04B0',
        [
          StringStruct(
            'CompanyName',
            {organization!r}
          ),
          StringStruct(
            'FileDescription',
            {description!r}
          ),
          StringStruct(
            'FileVersion',
            {app_version!r}
          ),
          StringStruct(
            'InternalName',
            'OpenFishReader'
          ),
          StringStruct(
            'LegalCopyright',
            {copyright_text!r}
          ),
          StringStruct(
            'OriginalFilename',
            'OpenFishReader.exe'
          ),
          StringStruct(
            'ProductName',
            {app_name!r}
          ),
          StringStruct(
            'ProductVersion',
            {app_version!r}
          )
        ]
      )
    ]),
    VarFileInfo([
      VarStruct(
        'Translation',
        [1036, 1200]
      )
    ])
  ]
)
"""

    OUTPUT_FILE.write_text(
        content,
        encoding="utf-8",
    )

    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
