#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import dingtalk_stream
from ad_operations import add_department_to_ad, remove_department_from_ad, modify_department_in_ad, manage_user_in_ad, remove_user_from_department, disable_and_move_user

# 钉钉API相关配置
DINGTALK_APP_KEY = 'ding6bepzc8u2buo7bck'
DINGTALK_APP_SECRET = 'U45fhOQCdjuZ1sZd11DHVdmKDdaLtzWllXbsFmzCSgdqoUGXODYY2runr-dgFbT4'

class MyEventHandler(dingtalk_stream.EventHandler):
    async def process(self, event: dingtalk_stream.EventMessage):
        event_type = event.headers.event_type
        self.logger.info(
            'received event, delay=%sms, eventType=%s, eventId=%s, eventBornTime=%d, eventCorpId=%s, '
            'eventUnifiedAppId=%s, data=%s',
            int(time.time() * 1000) - event.headers.event_born_time,
            event.headers.event_type,
            event.headers.event_id,
            event.headers.event_born_time,
            event.headers.event_corp_id,
            event.headers.event_unified_app_id,
            event.data)
        
        # 根据事件类型处理业务逻辑
        if event_type == 'org_dept_create':
            await self.handle_dept_create(event.data)
        elif event_type == 'org_dept_remove':
            await self.handle_dept_remove(event.data)
        elif event_type == 'org_dept_modify':
            await self.handle_dept_modify(event.data)
        elif event_type == 'user_add_org':
            await self.handle_user_add(event.data)
        elif event_type == 'user_leave_org':
            await self.handle_user_remove(event.data)
        elif event_type == 'user_modify_org':
            await self.handle_user_modify(event.data)
        
        return dingtalk_stream.AckMessage.STATUS_OK, 'OK'

    async def handle_dept_create(self, data):
        dept_id = data['deptId'][0]
        self.logger.info(f'Department created with ID: {dept_id}')
        add_department_to_ad(dept_id)

    async def handle_dept_remove(self, data):
        dept_ids = data['deptId']
        self.logger.info(f'Departments removed with IDs: {dept_ids}')
        for dept_id in dept_ids:
            remove_department_from_ad(dept_id)

    async def handle_dept_modify(self, data):
        dept_id = data['deptId'][0]
        self.logger.info(f'Department modified with ID: {dept_id}')
        modify_department_in_ad(dept_id)

    async def handle_user_add(self, data):
        user_ids = data['userId']
        self.logger.info(f'Users added with IDs: {user_ids}')
        for user_id in user_ids:
            manage_user_in_ad(user_id)

    async def handle_user_remove(self, data):
        user_ids = data['userId']
        self.logger.info(f'Users removed with IDs: {user_ids}')
        for user_id in user_ids:
            disable_and_move_user(user_id)

    async def handle_user_modify(self, data):
        user_ids = data['userId']
        self.logger.info(f'Users modified with IDs: {user_ids}')
        for user_id in user_ids:
            manage_user_in_ad(user_id)

def main():
    credential = dingtalk_stream.Credential(DINGTALK_APP_KEY, DINGTALK_APP_SECRET)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_all_event_handler(MyEventHandler())
    client.start_forever()

if __name__ == '__main__':
    main()
