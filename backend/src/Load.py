import pandas as pd
import sqlite3
import os


def load_csv_to_sqlite(csv_path, db_path, table_name="videos"):
    """
    Reads a processed CSV and loads it into a SQLite database.
    This completes the ETL (Extract, Transform, Load) pipeline.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Read the clean CSV
    df = pd.read_csv(csv_path)

    # Connect to SQLite (this automatically creates the file if it doesn't exist)
    conn = sqlite3.connect(db_path)

    # Write the data to a SQL table
    # if_exists='replace' means we overwrite the table every time we run the pipeline
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    print(f"✅ Successfully loaded {len(df)} rows into SQLite.")
    print(f"📁 Database saved at: {db_path} | Table: '{table_name}'")

    # Always close the connection
    conn.close()


if __name__ == "__main__":
    # Input from our previous step, Output to our new database
    csv_input = "../data/processed/eldentips_cleaned_videos.csv"
    db_output = "../data/database.sqlite"

    print("🔄 Starting Data Load Pipeline...")
    try:
        load_csv_to_sqlite(csv_input, db_output)
    except FileNotFoundError:
        print(f"❌ Error: Could not find {csv_input}. Run transform.py first.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")