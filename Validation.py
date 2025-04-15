import json
import logging
from jsonschema import validate
from jsonschema.exceptions import ValidationError

class Validation:
    def __init__(self):
        self._request_schema = self._load_schema('requestSchema.json')

    @staticmethod
    def _load_schema(schema_file):
        with open(schema_file, 'r') as file:
            return json.load(file)

    def _validate_json(self, data, request_schema, cv_schema):
        schema = {}

        # Merge properties from request_schema and cv_schema
        if 'properties' in request_schema and 'properties' in cv_schema:
            schema['properties'] = {**request_schema['properties'], **cv_schema['properties']}
        else:
            schema['properties'] = request_schema.get('properties', {}).copy()

        # Add 'required' from cv_schema if it exists
        if 'required' in cv_schema:
            schema['required'] = cv_schema['required']

        try:
            #validate(instance=json.loads(data), schema=schema)
            return True
        except ValidationError as e:
            logging.error(f"JSON data is invalid: {data}")
            logging.error(f"Error message: {e.message}")
            logging.error(f"Schema path: {' -> '.join(map(str, e.schema_path))}")
            logging.error(f"Instance path: {' -> '.join(map(str, e.path))}")
            return False

    def validate_request(self, request, cv_schema):
        return self._validate_json(json.dumps(request), self._request_schema, cv_schema)