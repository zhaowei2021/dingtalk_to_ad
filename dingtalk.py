#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import logging

# 钉钉API相关配置
DINGTALK_APP_KEY = 'ding6bepzc8u2buo7bck'
DINGTALK_APP_SECRET = 'U45fhOQCdjuZ1sZd11DHVdmKDdaLtzWllXbsFmzCSgdqoUGXODYY2runr-dgFbT4'

# 获取钉钉Access Token
def get_access_token():
    url = 'https://oapi.dingtalk.com/gettoken'
    params = {
        'appkey': DINGTALK_APP_KEY,
        'appsecret': DINGTALK_APP_SECRET
    }
    response = requests.get(url, params=params)
    response_data = response.json()
    logging.info(f'Access Token Response: {response_data}')
    return response_data['access_token']

# 获取部门信息
def get_department_info(dept_id):
    access_token = get_access_token()
    url = f'https://oapi.dingtalk.com/department/get?access_token={access_token}&id={dept_id}'
    response = requests.get(url)
    dept_info = response.json()
    logging.info(f'Department Info Response for ID {dept_id}: {dept_info}')
    return dept_info

# 获取部门名称
def get_department_name(dept_id):
    dept_info = get_department_info(dept_id)
    return dept_info.get('name', 'Unknown Department')

# 获取上级部门名称
def get_parent_department_name(dept_id):
    dept_info = get_department_info(dept_id)
    parent_id = dept_info.get('parentid')
    if parent_id:
        parent_info = get_department_info(parent_id)
        parent_name = parent_info.get('name')
        return parent_name
    return None

# 获取用户信息
def get_user_info(user_id):
    access_token = get_access_token()
    url = f'https://oapi.dingtalk.com/user/get?access_token={access_token}&userid={user_id}'
    response = requests.get(url)
    user_info = response.json()
    logging.info(f'User Info Response for ID {user_id}: {user_info}')
    return user_info
