#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ldap3 import Server, Connection, ALL, NTLM, MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
import logging
from dingtalk import get_department_name, get_parent_department_name, get_user_info

# 配置日志
logging.basicConfig(level=logging.INFO)

# AD服务器配置
AD_SERVER = '10.0.3.6'
AD_USER = 'volcano-force\\Administrator'
AD_PASSWORD = 'volcano@2021'
GROUP_BASE_DN = 'OU=groups,OU=volcano-force,DC=volcano-force,DC=local'
USER_BASE_DN = 'OU=private_users,OU=users,OU=volcano-force,DC=volcano-force,DC=local'
DISABLED_USER_DN = 'OU=users_disabled,OU=volcano-force,DC=volcano-force,DC=local'

def get_ad_connection():
    server = Server(AD_SERVER, port=636, use_ssl=True, get_info=ALL)
    conn = Connection(server, user=AD_USER, password=AD_PASSWORD, authentication=NTLM, auto_bind=True)
    return conn

def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def get_full_group_name(dept_id):
    parent_name = get_parent_department_name(dept_id)
    dept_name = get_department_name(dept_id)
    if parent_name == '北京原力棱镜科技有限公司' or not parent_name:
        return dept_name
    else:
        return f"{parent_name}-{dept_name}"

def add_department_to_ad(dept_id):
    dept_name = get_full_group_name(dept_id)
    conn = get_ad_connection()

    # 创建组
    group_dn = f'CN={dept_name},{GROUP_BASE_DN}'
    try:
        conn.add(group_dn, 'group', {'sAMAccountName': dept_name, 'gidNumber': dept_id})
        logging.info(f'Group {dept_name} created.')
    except Exception as e:
        logging.error(f'Failed to create group {dept_name}: {e}')

def remove_department_from_ad(dept_id):
    conn = get_ad_connection()

    # 查找组并删除
    if conn.search(GROUP_BASE_DN, f'(gidNumber={dept_id})', attributes=['distinguishedName']):
        if len(conn.entries) > 0:
            group_dn = conn.entries[0].entry_dn
            try:
                conn.delete(group_dn)
                logging.info(f'Group with gidNumber {dept_id} deleted. DN: {group_dn}')
            except Exception as e:
                logging.error(f'Failed to delete group with gidNumber {dept_id}: {e}')
        else:
            logging.error(f'No group found with gidNumber {dept_id}')
    else:
        logging.error(f'Failed to find group with gidNumber {dept_id}')
        
def modify_department_in_ad(dept_id):
    dept_name = get_full_group_name(dept_id)
    conn = get_ad_connection()

    # 查找组并修改名称
    if conn.search(GROUP_BASE_DN, f'(gidNumber={dept_id})', attributes=['cn']):
        entry = conn.entries[0]
        old_group_dn = entry.entry_dn
        new_rdn = f'CN={dept_name}'
        logging.info(f'Current group DN: {old_group_dn}')
        logging.info(f'Attempting to modify CN from {entry.cn.value} to {dept_name}')

        if old_group_dn.split(',')[0] != new_rdn:
            try:
                conn.modify_dn(old_group_dn, new_rdn)
                logging.info(f'Successfully renamed group from {old_group_dn} to {new_rdn},{GROUP_BASE_DN}.')
                conn.modify(f'{new_rdn},{GROUP_BASE_DN}', {'sAMAccountName': [(MODIFY_REPLACE, [dept_name])]})
                logging.info(f'Successfully updated sAMAccountName to {dept_name}.')
            except Exception as e:
                logging.error(f'Failed to rename group or update sAMAccountName: {e}')
        else:
            logging.info(f'Group name is already {dept_name}.')
    else:
        logging.error(f"Group with gidNumber {dept_id} not found for modification.")

def add_user_to_ad(user_info):
    user_name = user_info.get('name')
    user_email = user_info.get('orgEmail')
    user_id = user_info.get('userid')

    if not user_name or not user_email or not user_id:
        logging.error(f'User does not have a name, email or user ID.')
        return

    user_sAMAccountName = user_email.split('@')[0]
    user_dn = f'CN={user_name},{USER_BASE_DN}'
    password = generate_random_password()
    encoded_password = f'"{password}"'.encode('utf-16-le')
    logging.info(f"Generated password: {password}")

    conn = get_ad_connection()

    # 创建用户
    try:
        conn.add(user_dn, 'user', {
            'cn': user_name,
            'sAMAccountName': user_sAMAccountName,
            'mail': user_email,
            'unicodePwd': encoded_password,
            'userAccountControl': 512,  # Enable account
            'description': user_id
        })
        if conn.result['result'] == 0:
            logging.info(f'User {user_name} created with DN {user_dn}. Password: {password}')
        else:
            logging.error(f'Failed to create user {user_name}. LDAP error: {conn.result}')
    except Exception as e:
        logging.error(f'Failed to create user {user_name}: {e}')

def manage_user_in_ad(user_id):
    user_info = get_user_info(user_id)
    user_email = user_info.get('orgEmail')
    dept_ids = user_info.get('department')

    if not user_email or not dept_ids:
        logging.error(f'User {user_id} does not have an email or departments.')
        return

    conn = get_ad_connection()

    # 查找用户
    if not conn.search(USER_BASE_DN, f'(description={user_id})', attributes=['distinguishedName']):
        add_user_to_ad(user_info)

    if conn.search(USER_BASE_DN, f'(description={user_id})', attributes=['distinguishedName']):
        user_dn = conn.entries[0].entry_dn
        ad_groups = set()
        
        # 获取用户当前所属的AD组
        if conn.search(USER_BASE_DN, f'(description={user_id})', attributes=['memberOf']):
            ad_groups = {group.split(',')[0].split('=')[1] for group in conn.entries[0].memberOf}

        # 钉钉中的部门
        dingtalk_depts = {get_full_group_name(dept_id) for dept_id in dept_ids}

        # 需要添加的组
        groups_to_add = dingtalk_depts - ad_groups
        # 需要移除的组
        groups_to_remove = ad_groups - dingtalk_depts

        for dept_name in groups_to_add:
            group_dn = f'CN={dept_name},{GROUP_BASE_DN}'
            try:
                conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
                logging.info(f'User {user_dn} added to group {group_dn}.')
            except Exception as e:
                logging.error(f'Failed to add user {user_dn} to group {group_dn}: {e}')

        for dept_name in groups_to_remove:
            group_dn = f'CN={dept_name},{GROUP_BASE_DN}'
            try:
                conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
                logging.info(f'User {user_dn} removed from group {group_dn}.')
            except Exception as e:
                logging.error(f'Failed to remove user {user_dn} from group {group_dn}: {e}')
    else:
        logging.error(f'User with email {user_email} not found in AD.')

def remove_user_from_department(user_id):
    user_info = get_user_info(user_id)
    user_email = user_info.get('orgEmail')
    dept_ids = user_info.get('department')

    if not user_email or not dept_ids:
        logging.error(f'User {user_id} does not have an email or departments.')
        return
    
    conn = get_ad_connection()
    
    # 查找用户
    if conn.search(USER_BASE_DN, f'(description={user_id})', attributes=['distinguishedName']):
        user_dn = conn.entries[0].entry_dn
        for dept_id in dept_ids:
            dept_name = get_full_group_name(dept_id)
            group_dn = f'CN={dept_name},{GROUP_BASE_DN}'
            try:
                conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
                logging.info(f'User {user_dn} removed from group {group_dn}.')
            except Exception as e:
                logging.error(f'Failed to remove user {user_dn} from group {group_dn}: {e}')
    else:
        logging.error(f'User with description {user_id} not found in AD.')

def disable_and_move_user(user_id):
    conn = get_ad_connection()
    
    # 查找用户
    if conn.search(USER_BASE_DN, f'(description={user_id})', attributes=['distinguishedName', 'memberOf']):
        user_dn = conn.entries[0].entry_dn
        member_of_groups = conn.entries[0].memberOf

        try:
            # 禁用用户
            conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [514])]})  # 514 = Account disabled
            logging.info(f'User {user_dn} disabled.')

            # 移除用户所属的所有组
            for group_dn in member_of_groups:
                conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
                logging.info(f'User {user_dn} removed from group {group_dn}.')

            # 移动用户到指定的组织单元
            conn.modify_dn(user_dn, f'CN={user_dn.split(",")[0].split("=")[1]}', new_superior=DISABLED_USER_DN)
            logging.info(f'User {user_dn} moved to {DISABLED_USER_DN}.')
        except Exception as e:
            logging.error(f'Failed to disable and move user {user_dn}: {e}')
    else:
        logging.error(f'User with description {user_id} not found in AD.')
