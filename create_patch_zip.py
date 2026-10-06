import zipfile
import os

files_to_zip = [
    'patch_readme.md',
    'backend/app/models/arena.py',
    'backend/app/schemas/arena.py',
    'backend/app/api/prompt_bank.py',
    'backend/app/api/arena.py',
    'backend/app/services/arena_service.py',
    'backend/migrate_db.py'
]

zip_filename = 'PromptBankDynamicPatch.zip'

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in files_to_zip:
        if os.path.exists(file):
            zipf.write(file)
            print(f"Added {file}")
        else:
            print(f"Warning: {file} not found")

print(f"Successfully created {zip_filename}")
