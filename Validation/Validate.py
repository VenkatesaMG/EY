# validate_csv.py
import csv
import time
from NPI import lookup_npi
# from gemini_compare import compare_row_with_npi_gemini
from groq_compare import compare_row_with_npi_groq

def validate_csv_with_groq(
    input_csv_path: str,
    output_csv_path: str,
    sleep_between_npi_calls: float = 0.2,
) -> None:
    """
    For each row in the input CSV:
      1. Look up NPI from the registry.
      2. Ask Groq (Llama 3) to compare the row with NPI data.
      3. Write enriched row + Groq result to output CSV.
    """

    with open(input_csv_path, newline="", encoding="utf-8") as infile, \
         open(output_csv_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        base_fields = list(reader.fieldnames or [])

        extra_fields = [
            "npi_lookup_success",
            "groq_overall_match",
            "groq_confidence",
            "groq_issues",
            "groq_name_match",
            "groq_address_match",
            "groq_phone_match",
            "groq_specialty_match",
            "groq_explanation",
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
            row["groq_overall_match"] = ""
            row["groq_confidence"] = ""
            row["groq_issues"] = ""
            row["groq_name_match"] = ""
            row["groq_address_match"] = ""
            row["groq_phone_match"] = ""
            row["groq_specialty_match"] = ""
            row["groq_explanation"] = ""

            if npi_info:
                try:
                    groq_result = compare_row_with_npi_groq(row, npi_info)

                    row["groq_overall_match"] = groq_result.get("overall_match", "")
                    row["groq_confidence"] = groq_result.get("confidence", "")
                    row["groq_issues"] = ";".join(groq_result.get("issues", []))

                    fields = groq_result.get("fields", {})
                    row["groq_name_match"] = fields.get("name", {}).get("match", "")
                    row["groq_address_match"] = fields.get("address", {}).get("match", "")
                    row["groq_phone_match"] = fields.get("phone", {}).get("match", "")
                    row["groq_specialty_match"] = fields.get("specialty", {}).get("match", "")

                    # Truncate explanation so CSV doesn’t explode
                    explanation = groq_result.get("explanation", "") or ""
                    row["groq_explanation"] = explanation[:1000]

                except Exception as e:
                    print(f"[WARN] Groq compare failed on row {i}: {e}")

            writer.writerow(row)

    print(f"✓ Done. Wrote validation results to {output_csv_path}")

if __name__ == "__main__":
    validate_csv_with_groq(
        r"C:\Users\Dhile\Projects\Health Data Validation\EY\Data\clean_output.csv",
        r"C:\Users\Dhile\Projects\Health Data Validation\EY\Data\validated_groq.csv",
    )

