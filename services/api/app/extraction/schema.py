_FIELD = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "evidence": {"type": ["string", "null"]},
        "page": {"type": ["integer", "null"]},
    },
    "required": ["value", "evidence", "page"],
    "additionalProperties": False,
}

FIELD_KEYS = (
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
    "provider_name",
    "provider_npi",
)

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        **{k: _FIELD for k in FIELD_KEYS},
        "provider_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    # Non-nullable on purpose: the API allows at most 16 union-typed
                    # parameters per schema. "" / 0 mean unknown and are mapped to None.
                    "role": {"type": "string"},
                    "npi": {"type": "string"},
                    "page": {"type": "integer"},
                },
                "required": ["name", "role", "npi", "page"],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},  # "" = no notes (see union-type limit above)
    },
    "required": [*FIELD_KEYS, "provider_candidates", "notes"],
    "additionalProperties": False,
}
