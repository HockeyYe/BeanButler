import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.core.management import call_command

with open('data.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', 
                 indent=2,
                 exclude=[
                     'auth.permission',
                     'contenttypes',
                     'admin.logentry'  # 排除 admin_log
                 ],
                 stdout=f)

print("导出完成！data.json 已生成")