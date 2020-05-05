#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import uuid
from typing import Optional
# import json

from pymispobjecttemplates import Template, ObjectRelationships
import yaml

types_mapping = {
    'string': {'misp_attribute': 'text', "disable_correlation": True, 'multiple': True},
    'text': {'misp_attribute': 'text', "disable_correlation": True, 'multiple': True},
    'html': {'misp_attribute': 'text', "disable_correlation": True, 'multiple': True},
    'topic': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'name': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'address': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'checksum': {'misp_attribute': 'sha1', "disable_correlation": False, 'multiple': True},
    'country': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'date': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'email': {'misp_attribute': 'email-src', "disable_correlation": False, 'multiple': True},
    # 'entity': this is a relationship
    'iban': {'misp_attribute': 'iban', "disable_correlation": False, 'multiple': True},
    'identifier': {'misp_attribute': 'text', "disable_correlation": False, 'multiple': True},
    'ip': {'misp_attribute': 'ip-src', "disable_correlation": False, 'multiple': True},
    'json': {'misp_attribute': 'text', "disable_correlation": True, 'multiple': True},
    'language': {'misp_attribute': 'text', "disable_correlation": True, 'multiple': True},
    'mimetype': {'misp_attribute': 'mime-type', "disable_correlation": True, 'multiple': True},
    'number': {'misp_attribute': 'float', "disable_correlation": True, 'multiple': True},
    'phone': {'misp_attribute': 'phone-number', "disable_correlation": False, 'multiple': True},
    'url': {'misp_attribute': 'url', "disable_correlation": False, 'multiple': True}
}


class FTMSchemasToMISPObjects():

    def __init__(self, path: Path):
        self.relationships = ObjectRelationships()
        self.root_schemas = path
        self.schemas = {}
        for schema_path in self.root_schemas.glob('*.y*ml'):
            with schema_path.open() as f:
                for obj_name, description in yaml.safe_load(f.read()).items():
                    self.schemas[obj_name] = description

    def make_template(self, schema_name: str, existing_template: Optional[Template]=None):
        s = self.schemas[schema_name]

        if s.get('edge'):
            # We have a relationship, add it in the defualt list in MISP is needed
            rel_name = '-'.join(s['edge']['label'].split())
            relationship = self.relationships.get_relationship(rel_name)
            if not relationship:
                # new relationship
                self.relationships.set_relationship(name=rel_name,
                                                    description=s['edge']['label'],
                                                    rel_format=['followthemoney'])
            elif 'followthemoney' not in relationship['format']:
                # Add format in list
                relationship['format'].append('followthemoney')
                self.relationships.set_relationship(**relationship)
            else:
                # Nothing to do.
                pass

        if existing_template:
            # Adding entries from parent template into child
            template = existing_template
        elif s.get('abstract'):
            # Just ignore that.
            return
        else:
            # Create a new template
            template = Template(name=f'ftm-{schema_name}', version=1, description=s.get('description', ''),
                                uuid=str(uuid.uuid4()), attributes={}, **{'meta-category': 'followthemoney'})

        if s.get('required'):
            template.add_required(s['required'])

        if s.get('extends'):
            # The schema extends an other one. As MISP Templates do not have inheritance, we import all these entries in the template
            if isinstance(s['extends'], str):
                template = self.make_template(s['extends'], template)
            else:
                for extended in s['extends']:
                    template = self.make_template(extended, template)
        if 'properties' not in s:
            return template

        for object_relation, details in s['properties'].items():
            if 'type' not in details:
                attribute_type = 'string'
            elif details['type'] == 'entity':
                # This is a relationship, will be represented appropriately in the script
                continue
            else:
                attribute_type = details['type']
            if 'featured' in s:
                ui_priority = 1 if object_relation in s['featured'] else 0
            else:
                ui_priority = 0
            if 'description' in details:
                description = details['description']
            elif 'label' in details:
                description = details['label']
            else:
                print(details)
                description = ''
            template.set_attribute(object_relation=object_relation, ui_priority=ui_priority,
                                   description=description, **types_mapping[attribute_type])

        if hasattr(template, 'required'):
            # NOTE: a required key in the FTM schema may be a relationship (exemple: taxee in TaxRoll), removing it
            template.required = [attribute_name for attribute_name in template.required
                                 if attribute_name in set(template.attributes.keys())]
            if not template.required:
                del template.required
        return template

    def make_templates(self):
        self.templates = []
        for schema_name in self.schemas.keys():
            template = self.make_template(schema_name)
            if template:
                self.templates.append(template)

        for template in self.templates:
            template.validate()

    def dump(self):
        for template in self.templates:
            template.dump()
        self.relationships.dump()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert Follow The Money schemas to MISP objects.')
    parser.add_argument("-p", "--path", required=True, type=Path, help="Path to schemas")
    args = parser.parse_args()

    converter = FTMSchemasToMISPObjects(args.path)
    converter.make_templates()
    converter.dump()
