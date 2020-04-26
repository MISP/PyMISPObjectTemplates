#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import MutableMapping
from pathlib import Path
import sys
import json
from typing import Dict, Optional, Union, List

from jsonschema import validate  # type: ignore

root_dir: Path = Path(sys.modules['pymispobjecttemplates'].__file__).parent / 'data' / 'misp-objects'
with (root_dir / 'schema_objects.json').open() as f:
    schema_objects = json.load(f)

with (root_dir / 'schema_relationships.json').open() as f:
    schema_relationships = json.load(f)


class Template():

    def __init__(self, **template):
        self.name = template['name']
        self.version = int(template['version'])
        self.description = template['description']
        self.meta_category = template['meta-category']
        self.uuid = template['uuid']
        self.attributes = template['attributes']

        if 'required' in template:
            self.required = template['required']
        if 'requiredOneOf' in template:
            self.required_one_of = template['requiredOneOf']

    def to_dict(self) -> Dict:
        to_return = {'name': self.name, 'version': self.version,
                     'description': self.description, 'meta-category': self.meta_category,
                     'uuid': self.uuid, 'attributes': self.attributes}
        if hasattr(self, 'required'):
            to_return['required'] = self.required
        if hasattr(self, 'required_one_of'):
            to_return['requiredOneOf'] = self.required_one_of
        return to_return

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def validate(self):
        validate(instance=self.to_dict(), schema=schema_objects)

    def dump(self):
        self.validate()
        definition_file = root_dir / 'objects' / self.name / 'definition.json'
        if not definition_file.parent.exists():
            definition_file.parent.mkdir()
            new_template = self.to_dict()
        else:
            with definition_file.open() as f:
                existing_template = Template(**json.load(f)).to_dict()
            existing_template_version = existing_template.pop('version')

            self.uuid = existing_template['uuid']
            new_template = self.to_dict()
            new_template_version = new_template.pop('version')

            if existing_template == new_template:
                print(f'No changes in {self.name}')
                # No changes, no dump
                return
            elif new_template_version > existing_template_version:
                new_template['version'] = new_template_version
            else:
                new_template['version'] = existing_template_version + 1

        with (root_dir / 'objects' / self.name / 'definition.json').open('w') as f:
            json.dump(new_template, f, indent=2, ensure_ascii=False, sort_keys=True)

    def add_required(self, required_attributes: List[str]):
        if not hasattr(self, 'required'):
            self.required = []
        self.required += required_attributes
        self.required = list(set(self.required))

    def get_attribute(self, object_relation: str):
        return self.attributes.get(object_relation)

    def set_attribute(self, object_relation: str, misp_attribute: str, ui_priority: int, description: str,
                      categories: Optional[List[str]]=None,
                      disable_correlation: Optional[bool]=None,
                      multiple: Optional[bool]=None,
                      recommended: Optional[bool]=None,
                      sane_default: Optional[List[str]]=None,
                      to_ids: Optional[bool]=None,
                      values_list: Optional[List[str]]=None):
        attribute = {'misp-attribute': misp_attribute, 'ui-priority': ui_priority, 'description': description}
        if categories is not None:
            attribute['categories'] = categories
        if disable_correlation is not None:
            attribute['disable_correlation'] = disable_correlation
        if multiple is not None:
            attribute['multiple'] = multiple
        if recommended is not None:
            attribute['recommended'] = recommended
        if sane_default is not None:
            attribute['sane_default'] = sane_default
        if to_ids is not None:
            attribute['to_ids'] = to_ids
        if values_list is not None:
            attribute['values_list'] = values_list
        self.attributes[object_relation] = attribute
        return attribute


class ObjectTemplates(MutableMapping):

    def __init__(self):
        self._templates: Dict[str, Template] = {}
        for obj_template_path in root_dir.glob('objects/*/definition.json'):
            with obj_template_path.open() as _f:
                template = Template(**json.load(_f))
                self[template.name] = template

    def dump(self):
        for template_name, template in self.items():
            template.dump()

    def __getitem__(self, template_name: str) -> Template:
        return self._templates[template_name]

    def __setitem__(self, template_name: str, template: Template):
        self._templates[template_name] = template

    def __delitem__(self, template_name: str):
        del self._templates[template_name]

    def __iter__(self):
        return iter(self._templates)

    def __len__(self):
        return len(self._templates)


class ObjectRelationships():

    def __init__(self):
        with (root_dir / 'relationships' / 'definition.json').open() as f:
            rel = json.load(f)
        self.version = rel['version']
        self.description = rel['description']
        self.uuid = rel['uuid']
        self.name = rel['name']
        self._values = rel['values']

    def to_dict(self):
        return {'version': self.version, 'description': self.description, 'uuid': self.uuid,
                'name': self.name, 'values': self._values}

    def dump(self):
        with (root_dir / 'relationships' / 'definition.json').open('w') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, sort_keys=True)

    def validate(self):
        validate(instance=self.to_dict(), schema=schema_relationships)

    def get_relationship(self, name: str) -> Optional[Dict]:
        for value in self._values:
            if value['name'] == name:
                return value
        else:
            return None

    def set_relationship(self, name: str, description: Optional[str]=None,
                         rel_format: Optional[Union[str, List[str]]]=None):
        exists = self.get_relationship(name)

        for value in self._values:
            if value['name'] == name:
                if description:
                    value['description'] = description
                if rel_format:
                    if isinstance(rel_format, str):
                        value['format'].append(rel_format)
                    else:
                        value['format'] = list(set().union(exists['format'], rel_format))  # type: ignore
                break
        else:
            if not description:
                raise Exception('description is required for a new relationship')
            if not rel_format:
                raise Exception('rel_format is required for a new relationship')
            value = {'name': name, 'description': description}
            if isinstance(rel_format, str):
                value['format'] = [rel_format]
            else:
                value['format'] = rel_format
            self._values.append(value)
