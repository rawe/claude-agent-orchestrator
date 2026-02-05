"""
Sample Output Schemas

JSON Schemas for testing output validation.
"""

# Simple schema requiring a name field
SIMPLE_NAME_SCHEMA = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {
            "type": "string",
            "description": "A person's name"
        }
    },
    "additionalProperties": False
}

# Simple schema requiring a number value
SIMPLE_NUMBER_SCHEMA = {
    "type": "object",
    "required": ["value"],
    "properties": {
        "value": {
            "type": "integer",
            "description": "A numeric value"
        }
    },
    "additionalProperties": False
}

# Schema with multiple required fields
SUMMARY_SCORE_SCHEMA = {
    "type": "object",
    "required": ["summary", "score"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "A brief summary"
        },
        "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "A score from 0 to 100"
        }
    },
    "additionalProperties": False
}

# Schema with nested object
NESTED_OBJECT_SCHEMA = {
    "type": "object",
    "required": ["person"],
    "properties": {
        "person": {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            }
        }
    },
    "additionalProperties": False
}

# Schema with array
ITEMS_ARRAY_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        }
    },
    "additionalProperties": False
}

# Schema that's hard to satisfy (for retry testing)
STRICT_SCHEMA = {
    "type": "object",
    "required": ["code", "message", "timestamp"],
    "properties": {
        "code": {
            "type": "integer",
            "enum": [200, 201, 400, 404, 500]
        },
        "message": {
            "type": "string",
            "minLength": 10,
            "maxLength": 100
        },
        "timestamp": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
        }
    },
    "additionalProperties": False
}

# Boolean result schema
BOOLEAN_RESULT_SCHEMA = {
    "type": "object",
    "required": ["success"],
    "properties": {
        "success": {
            "type": "boolean"
        },
        "error": {
            "type": "string"
        }
    },
    "additionalProperties": False
}
