import sys
with open('backend/app/api/prompt_bank.py', 'r', encoding='utf-8') as f:
    text = f.read()

put_idx = text.find('@router.put("/{item_id}")')
demo_idx = text.find('from fastapi import UploadFile, File')

if put_idx != -1 and demo_idx != -1:
    before = text[:put_idx]
    put_and_delete = text[put_idx:demo_idx]
    the_rest = text[demo_idx:]
    new_text = before + the_rest + '\n\n' + put_and_delete
    with open('backend/app/api/prompt_bank.py', 'w', encoding='utf-8') as fw:
        fw.write(new_text)
    print('Successfully reordered routes.')
else:
    print('Error finding indices.')
