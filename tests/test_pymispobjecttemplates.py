import unittest

from pymispobjecttemplates import __version__
from pymispobjecttemplates import ObjectTemplates, ObjectRelationships, Template
import uuid


def test_version():
    assert __version__ == '0.1.0'


class TestPyMISPObjectTemplates(unittest.TestCase):

    def setUp(self):
        self.object_templates = ObjectTemplates()
        self.object_relationships = ObjectRelationships()

    def test_load(self):
        for template_name, template in self.object_templates.items():
            template.validate()

    def test_required_exists(self):
        for template_name, template in self.object_templates.items():
            if hasattr(template, 'required'):
                self.assertTrue(set(template.required).issubset(set(template.attributes.keys())),
                                f'{template_name} One of the entries in "required" is not a valid object relation.')
            if hasattr(template, 'required_one_of'):
                self.assertTrue(set(template.required_one_of).issubset(set(template.attributes.keys())),
                                f'{template_name} One of the entries in "required_one_of" is not a valid object relation.')

    def test_unique_uuid(self):
        uuids = {}
        for template_name, template in self.object_templates.items():
            self.assertIsNone(uuids.get(template.uuid), f'Same uuid for {template_name} and {uuids.get("template.uuid")} ({template.uuid})')
            uuids[template.uuid] = template_name

    def test_get_attribute(self):
        attribute = self.object_templates['file'].get_attribute('md5')
        self.assertEqual(attribute['misp-attribute'], 'md5')

    def test_create_template(self):
        new_template = Template(name='test_template', version=0, description='This is a test template',
                                uuid=str(uuid.uuid4()), attributes={}, **{'meta-category': 'file'})
        new_template.set_attribute(object_relation='testattribute', misp_attribute='text',
                                   ui_priority=0, description='Test Attribute')
        new_template.validate()

    def test_dump(self):
        for template_name, template in self.object_templates.items():
            template.dump()

    def test_relationships_load(self):
        self.object_relationships.validate()

    def test_relationship_get(self):
        object_relationships = ObjectRelationships()
        r = object_relationships.get_relationship('derived-from')
        self.assertEqual(r['name'], 'derived-from')

    def test_relationship_add(self):
        object_relationships = ObjectRelationships()
        object_relationships.set_relationship(name='__new_testcase', description='blah', rel_format='baz')
        object_relationships.validate()
        r = object_relationships.get_relationship('__new_testcase')
        self.assertEqual(r['description'], 'blah')

    def test_relationships_dump(self):
        self.object_relationships.dump()
