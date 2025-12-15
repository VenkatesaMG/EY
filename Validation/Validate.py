# validate_csv.py
import csv
import time
from NPI import lookup_npi
from gemini_compare import compare_row_with_npi_gemini

def validate_csv_with_gemini(
    input_csv_path: str,
    output_csv_path: str,
    sleep_between_npi_calls: float = 0.2,
) -> None:
    """
    For each row in the input CSV:
      1. Look up NPI from the registry.
      2. Ask Gemini to compare the row with NPI data.
      3. Write enriched row + Gemini result to output CSV.
    """

    with open(input_csv_path, newline="", encoding="utf-8") as infile, \
         open(output_csv_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        base_fields = list(reader.fieldnames or [])

        extra_fields = [
            "npi_lookup_success",
            "gemini_overall_match",
            "gemini_confidence",
            "gemini_issues",
            "gemini_name_match",
            "gemini_address_match",
            "gemini_phone_match",
            "gemini_specialty_match",
            "gemini_explanation",
        ]
        fieldnames = base_fields + [f for f in extra_fields if f not in base_fields]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(reader, start=1):
            npi = (row.get("npi") or "").strip()
            print(f"[{i}] Processing NPI={npi}...")

            npi_info = lookup_npi(npi) if npi else None
            time.sleep(sleep_between_npi_calls)  # be kind to NPPES API

            # Default values
            row["npi_lookup_success"] = bool(npi_info)
            row["gemini_overall_match"] = ""
            row["gemini_confidence"] = ""
            row["gemini_issues"] = ""
            row["gemini_name_match"] = ""
            row["gemini_address_match"] = ""
            row["gemini_phone_match"] = ""
            row["gemini_specialty_match"] = ""
            row["gemini_explanation"] = ""

            if npi_info:
                try:
                    gemini_result = compare_row_with_npi_gemini(row, npi_info)

                    row["gemini_overall_match"] = gemini_result.get("overall_match", "")
                    row["gemini_confidence"] = gemini_result.get("confidence", "")
                    row["gemini_issues"] = ";".join(gemini_result.get("issues", []))

                    fields = gemini_result.get("fields", {})
                    row["gemini_name_match"] = fields.get("name", {}).get("match", "")
                    row["gemini_address_match"] = fields.get("address", {}).get("match", "")
                    row["gemini_phone_match"] = fields.get("phone", {}).get("match", "")
                    row["gemini_specialty_match"] = fields.get("specialty", {}).get("match", "")

                    # Truncate explanation so CSV doesn’t explode
                    explanation = gemini_result.get("explanation", "") or ""
                    row["gemini_explanation"] = explanation[:1000]

                except Exception as e:
                    print(f"[WARN] Gemini compare failed on row {i}: {e}")

            writer.writerow(row)

    print(f"✓ Done. Wrote validation results to {output_csv_path}")

if __name__ == "__main__":
    validate_csv_with_gemini(
        r"C:\Users\Dhile\Projects\Health Data Validation\EY\Data\clean_output.csv",
        r"C:\Users\Dhile\Projects\Health Data Validation\EY\Data\validated_gemini.csv",
    )

