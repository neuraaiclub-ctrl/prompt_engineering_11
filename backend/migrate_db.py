import sqlite3

def run_migration():
    conn = sqlite3.connect('hackathon_platform.db')
    cursor = conn.cursor()
    
    # Check and add dataset_tag to prompt_bank_items
    try:
        cursor.execute("ALTER TABLE prompt_bank_items ADD COLUMN dataset_tag VARCHAR NOT NULL DEFAULT 'default'")
        print("Added dataset_tag to prompt_bank_items")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("dataset_tag already exists in prompt_bank_items")
        else:
            raise e
            
    # Check and add active_dataset_tag to arena_config
    try:
        cursor.execute("ALTER TABLE arena_config ADD COLUMN active_dataset_tag VARCHAR NOT NULL DEFAULT 'default'")
        print("Added active_dataset_tag to arena_config")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("active_dataset_tag already exists in arena_config")
        else:
            raise e
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_migration()
