#!/usr/bin/env python3
"""Add admin user to config.json"""
import json
import hashlib
import os

CONFIG_PATH = '/var/www/leaderboard/data/config.json'

email = 'jeskigawa@gmail.com'
password = '9high2024'
password_hash = hashlib.sha256(password.encode()).hexdigest()

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

users = config.get('users', [])
users = [u for u in users if u.get('email', '').lower() != email.lower()]
users.append({
    'email': email,
    'password_hash': password_hash,
    'role': 'admin'
})
config['users'] = users

with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print('Done!')
print('Email:   ', email)
print('Password: 9high2024')
print('Please change your password after logging in.')
