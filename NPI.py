import requests

NPI_BASE_URL = "https://npiregistry.cms.hhs.gov/api/"

class NpiLookupError(Exception):
    pass

def lookup_npi(npi_number: str, pretty: bool = False) -> dict | None:
    """
    Look up a single NPI (10-digit string) via NPPES API v2.1.
    Returns a normalized dict for the first match, or None if not found.
    Raises NpiLookupError on HTTP / API errors.
    """
    params = {
        "version": "2.1",
        "number": npi_number,
        "limit": 1,        # we only care about this exact NPI
        "pretty": "on" if pretty else "off",
    }

    try:
        resp = requests.get(NPI_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise NpiLookupError(f"HTTP error calling NPPES: {e}") from e

    data = resp.json()

    # NPPES wraps results in a 'results' array; empty if no match. [web:1][web:53]
    results = data.get("results", [])
    if not results:
        return None

    raw = results[0]

    # Normalize common fields you’ll use later
    basic = raw.get("basic", {})                   # name, credential, etc. [web:53]
    taxonomies = raw.get("taxonomies", [])         # array of specialties
    addresses = raw.get("addresses", [])           # first = primary practice, second = mailing [web:1]

    primary_practice = addresses[0] if len(addresses) >= 1 else {}
    mailing_address = addresses[1] if len(addresses) >= 2 else {}

    normalized = {
        "npi": raw.get("number"),
        "enumeration_type": raw.get("enumeration_type"),
        "status": basic.get("status"),
        "first_name": basic.get("first_name"),
        "last_name": basic.get("last_name"),
        "credential": basic.get("credential"),
        "sole_proprietor": basic.get("sole_proprietor"),
        "gender": basic.get("gender"),
        "last_updated": basic.get("last_updated"),
        "primary_taxonomy": taxonomies[0] if taxonomies else None,
        "all_taxonomies": taxonomies,
        "primary_practice_address": {
            "address_1": primary_practice.get("address_1"),
            "address_2": primary_practice.get("address_2"),
            "city": primary_practice.get("city"),
            "state": primary_practice.get("state"),
            "postal_code": primary_practice.get("postal_code"),
            "telephone_number": primary_practice.get("telephone_number"),
            "country_code": primary_practice.get("country_code"),
        } if primary_practice else None,
        "mailing_address": {
            "address_1": mailing_address.get("address_1"),
            "address_2": mailing_address.get("address_2"),
            "city": mailing_address.get("city"),
            "state": mailing_address.get("state"),
            "postal_code": mailing_address.get("postal_code"),
            "telephone_number": mailing_address.get("telephone_number"),
            "country_code": mailing_address.get("country_code"),
        } if mailing_address else None,
        "raw": raw,  # keep full JSON for debugging / later use
    }

    return normalized



if __name__ == "__main__":
    test_npi = "1891106191"  # replace with a real NPI for local testing
    result = lookup_npi(test_npi)
    if result is None:
        print("No provider found for that NPI")
    else:
        # print(f"NPI: {result['npi']}")
        # print(f"Name: {result['first_name']} {result['last_name']}")
        # print(f"Primary taxonomy: {result['primary_taxonomy']}")
        # print(f"Primary practice city/state: "
        #       f"{result['primary_practice_address']['city']}, "
        #       f"{result['primary_practice_address']['state']}")

        print(result['primary_practice_address'])   # print the primary practice address

