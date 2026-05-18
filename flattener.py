#!/usr/bin/env python

from pymysql import connect
from pymysql.cursors import DictCursor
from yaml import safe_load
from argparse import ArgumentParser, FileType

ap = ArgumentParser()
ap.add_argument('--config-file', type=FileType('r'), default='config.yml', help="YAML config with MySQL values")

args = ap.parse_args()

config = safe_load(args.config_file)

regular_tables = [
    'accession',
    'archival_object',
    'assessment',
    'assessment_attribute_definition',
    'classification',
    'classification_term',
    'custom_report_template',
    'digital_object',
    'digital_object_component',
    'event',
    'resource',
    'rights_statement',
    'rights_statement_pre_088',
    'top_container'
]

wipe_tables = [
    'default_values',
    'required_fields'
]

# groups have to be handled separately



conn = connect(**config['mysql'])
conn.cursorclass = DictCursor

try:
    cur = conn.cursor()
    for table in regular_tables:
        cur.execute(f'UPDATE `{table}` SET repo_id = 2 WHERE repo_id <> 1')
    for table in wipe_tables:
        cur.execute(f'DELETE FROM `{table}` WHERE repo_id > 2')

    # group_code -> (set(ids of discarded repos with this group name), id of this group for repo_id=2,)
    group_code2id_mapping = {}
    all_bad_ids = set()
    cur.execute('SELECT group_code, id FROM `group` WHERE repo_id=2')
    for row in cur.fetchall():
        group_code2id_mapping[row['group_code']] = (set(), row['id'],)
    for name in group_code2id_mapping:
        cur.execute('SELECT id FROM `group` WHERE group_code = %s AND repo_id > 2', name)
        for row in cur.fetchall():
            group_code2id_mapping[name][0].add(row['id'])
            all_bad_ids.add(row['id'])
    for name in group_code2id_mapping:
        bad_ids, good_id = group_code2id_mapping[name]
        cur.execute('UPDATE group_user SET group_id = %s WHERE group_id IN %s', (good_id, bad_ids,))
    # Now that all users are solely in repo_id=2 groups, clean up bad groups
    cur.execute('DELETE FROM group_permission WHERE group_id IN %s', (all_bad_ids,))
    cur.execute('DELETE FROM `group` WHERE id IN %s', (all_bad_ids,))
    conn.commit()
finally:
    conn.close()
    args.config_file.close()



