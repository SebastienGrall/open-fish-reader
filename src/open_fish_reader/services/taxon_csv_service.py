from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..database.connection import open_database

CSV_FIELDS = (
    "tax_code",
    "common_name",
    "scientific_name",
    "sandre_code",
    "stage_code",
    "is_active",
    "keyboard_shortcut",
    "display_order",
)

_TRUE_VALUES = {
    "1",
    "true",
    "oui",
    "yes",
}

_FALSE_VALUES = {
    "",
    "0",
    "false",
    "non",
    "no",
}


class TaxonCsvService:
    def export_station_catalog(
        self,
        database_path: Path,
        output_path: Path,
    ) -> None:
        connection = open_database(database_path)

        try:
            rows = connection.execute(
                """
                SELECT
                    tax_code,
                    common_name,
                    scientific_name,
                    sandre_code,
                    stage_code,
                    is_active,
                    keyboard_shortcut,
                    display_order
                FROM taxa
                WHERE is_archived = 0
                ORDER BY
                    display_order,
                    tax_code
                """
            ).fetchall()

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with output_path.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=CSV_FIELDS,
                    delimiter=";",
                    extrasaction="ignore",
                )

                writer.writeheader()

                for row in rows:
                    writer.writerow(
                        {
                            "tax_code": row["tax_code"],
                            "common_name": row["common_name"],
                            "scientific_name": row["scientific_name"],
                            "sandre_code": (row["sandre_code"] or ""),
                            "stage_code": (row["stage_code"] or ""),
                            "is_active": int(bool(row["is_active"])),
                            "keyboard_shortcut": (row["keyboard_shortcut"] or ""),
                            "display_order": row["display_order"],
                        }
                    )

        finally:
            connection.close()

    def import_station_catalog(
        self,
        database_path: Path,
        input_path: Path,
    ) -> int:
        connection = open_database(database_path)

        try:
            valid_stages = {
                str(row["stage_code"])
                for row in connection.execute(
                    """
                    SELECT stage_code
                    FROM development_stages
                    WHERE is_active = 1
                    """
                ).fetchall()
            }

            parsed_rows = self._read_and_validate_csv(
                input_path,
                valid_stages,
            )

            self._validate_existing_shortcuts(
                connection,
                parsed_rows,
            )

            now = datetime.now().astimezone().isoformat(timespec="milliseconds")

            with connection:
                for parsed_row in parsed_rows:
                    self._upsert_taxon(
                        connection=connection,
                        parsed_row=parsed_row,
                        now=now,
                    )

            return len(parsed_rows)

        finally:
            connection.close()

    def _read_and_validate_csv(
        self,
        input_path: Path,
        valid_stages: set[str],
    ) -> list[dict[str, object]]:
        parsed_rows: list[dict[str, object]] = []

        seen_codes: dict[str, int] = {}
        seen_shortcuts: dict[str, int] = {}

        with input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            reader = csv.DictReader(
                stream,
                delimiter=";",
            )

            missing_columns = set(CSV_FIELDS) - set(reader.fieldnames or ())

            if missing_columns:
                raise ValueError("Colonnes CSV manquantes : " + ", ".join(sorted(missing_columns)))

            for line_number, row in enumerate(
                reader,
                start=2,
            ):
                parsed_row = self._parse_row(
                    row=row,
                    line_number=line_number,
                    valid_stages=valid_stages,
                )

                code = str(parsed_row["tax_code"])

                previous_code_line = seen_codes.get(code)

                if previous_code_line is not None:
                    raise ValueError(
                        f"Lignes "
                        f"{previous_code_line} et "
                        f"{line_number} : le code "
                        f"{code!r} est présent "
                        "plusieurs fois."
                    )

                seen_codes[code] = line_number

                shortcut = parsed_row["keyboard_shortcut"]

                if shortcut is not None:
                    shortcut_text = str(shortcut)

                    previous_shortcut_line = seen_shortcuts.get(shortcut_text)

                    if previous_shortcut_line is not None:
                        raise ValueError(
                            f"Lignes "
                            f"{previous_shortcut_line} "
                            f"et {line_number} : le "
                            f"raccourci "
                            f"{shortcut_text!r} est "
                            "utilisé plusieurs fois."
                        )

                    seen_shortcuts[shortcut_text] = line_number

                parsed_rows.append(parsed_row)

        return parsed_rows

    @staticmethod
    def _parse_row(
        row: dict[str, str | None],
        line_number: int,
        valid_stages: set[str],
    ) -> dict[str, object]:
        code = (row.get("tax_code") or "").strip().upper()

        if not 1 <= len(code) <= 10:
            raise ValueError(
                f"Ligne {line_number} : "
                f"le code court {code!r} doit "
                "contenir entre 1 et "
                "10 caractères."
            )

        if not all(character.isalnum() or character in {"_", "-"} for character in code):
            raise ValueError(
                f"Ligne {line_number} : "
                f"le code court {code!r} ne "
                "peut contenir que des lettres, "
                "des chiffres, '_' ou '-'."
            )

        common_name = (row.get("common_name") or "").strip()

        if not common_name:
            raise ValueError(f"Ligne {line_number} : le nom commun est obligatoire.")

        scientific_name = (row.get("scientific_name") or "").strip()

        if not scientific_name:
            raise ValueError(f"Ligne {line_number} : le nom scientifique est obligatoire.")

        sandre_code = (row.get("sandre_code") or "").strip() or None

        stage_code = (row.get("stage_code") or "").strip().upper() or None

        if stage_code is not None and stage_code not in valid_stages:
            raise ValueError(f"Ligne {line_number} : stade inconnu {stage_code!r}.")

        shortcut = (row.get("keyboard_shortcut") or "").strip().upper() or None

        if shortcut is not None and (len(shortcut) != 1 or not shortcut.isalnum()):
            raise ValueError(
                f"Ligne {line_number} : "
                f"le raccourci "
                f"{shortcut!r} doit contenir "
                "une seule lettre ou "
                "un seul chiffre."
            )

        active_text = (row.get("is_active") or "").strip().casefold()

        if active_text in _TRUE_VALUES:
            is_active = True
        elif active_text in _FALSE_VALUES:
            is_active = False
        else:
            raise ValueError(
                f"Ligne {line_number} : valeur is_active inconnue {active_text!r}. Utilisez 0 ou 1."
            )

        order_text = (row.get("display_order") or "").strip()

        try:
            display_order = int(order_text) if order_text else 0
        except ValueError as error:
            raise ValueError(
                f"Ligne {line_number} : ordre d'affichage invalide {order_text!r}."
            ) from error

        if display_order < 0:
            raise ValueError(f"Ligne {line_number} : l'ordre d'affichage ne peut pas être négatif.")

        return {
            "line_number": line_number,
            "tax_code": code,
            "common_name": common_name,
            "scientific_name": (scientific_name),
            "sandre_code": sandre_code,
            "stage_code": stage_code,
            "is_active": is_active,
            "keyboard_shortcut": shortcut,
            "display_order": display_order,
        }

    @staticmethod
    def _validate_existing_shortcuts(
        connection: sqlite3.Connection,
        parsed_rows: list[dict[str, object]],
    ) -> None:
        imported_codes = {str(row["tax_code"]) for row in parsed_rows}

        imported_shortcuts = {
            str(row["keyboard_shortcut"]): (
                str(row["tax_code"]),
                int(row["line_number"]),
            )
            for row in parsed_rows
            if row["is_active"] and row["keyboard_shortcut"] is not None
        }

        if not imported_shortcuts:
            return

        placeholders = ", ".join("?" for _code in imported_codes)

        query = f"""
            SELECT
                tax_code,
                keyboard_shortcut
            FROM taxa
            WHERE is_archived = 0
              AND is_active = 1
              AND keyboard_shortcut IS NOT NULL
              AND tax_code NOT IN (
                  {placeholders}
              )
        """

        existing_rows = connection.execute(
            query,
            tuple(imported_codes),
        ).fetchall()

        for existing_row in existing_rows:
            shortcut = str(existing_row["keyboard_shortcut"]).upper()

            imported = imported_shortcuts.get(shortcut)

            if imported is None:
                continue

            imported_code, line_number = imported

            raise ValueError(
                f"Ligne {line_number} : "
                f"le raccourci "
                f"{shortcut!r} demandé pour "
                f"{imported_code} est déjà "
                "utilisé par le taxon "
                f"{existing_row['tax_code']}."
            )

    @staticmethod
    def _upsert_taxon(
        connection: sqlite3.Connection,
        parsed_row: dict[str, object],
        now: str,
    ) -> None:
        try:
            connection.execute(
                """
                INSERT INTO taxa (
                    taxon_uuid,
                    reference_id,
                    tax_code,
                    stage_code,
                    common_name,
                    sandre_code,
                    scientific_name,
                    is_active,
                    keyboard_shortcut,
                    display_order,
                    source_type,
                    is_archived,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?,
                    NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'csv',
                    0,
                    ?,
                    ?
                )
                ON CONFLICT(tax_code)
                DO UPDATE SET
                    stage_code =
                        excluded.stage_code,
                    common_name =
                        excluded.common_name,
                    sandre_code =
                        excluded.sandre_code,
                    scientific_name =
                        excluded.scientific_name,
                    is_active =
                        excluded.is_active,
                    keyboard_shortcut =
                        excluded.keyboard_shortcut,
                    display_order =
                        excluded.display_order,
                    is_archived = 0,
                    updated_at =
                        excluded.updated_at
                """,
                (
                    str(uuid4()),
                    parsed_row["tax_code"],
                    parsed_row["stage_code"],
                    parsed_row["common_name"],
                    parsed_row["sandre_code"],
                    parsed_row["scientific_name"],
                    int(bool(parsed_row["is_active"])),
                    parsed_row["keyboard_shortcut"],
                    parsed_row["display_order"],
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as error:
            line_number = parsed_row["line_number"]

            raise ValueError(
                f"Ligne {line_number} : la ligne ne peut pas être importée : {error}."
            ) from error
