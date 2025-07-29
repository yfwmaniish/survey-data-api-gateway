#!/usr/bin/env python3
"""
Universal Survey Data Importer
Supports: CSV, JSON, Excel, SQL dumps, PostgreSQL format
"""

import sqlite3
import pandas as pd
import json
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SurveyDataImporter:
    """Universal importer for survey data in various formats"""
    
    def __init__(self, db_path: str = "survey_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.setup_database()
    
    def setup_database(self):
        """Ensure database tables exist"""
        cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            created_date DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'active'
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY,
            survey_id INTEGER,
            respondent_age INTEGER,
            respondent_gender TEXT,
            response_text TEXT,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (survey_id) REFERENCES surveys (id)
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS demographics (
            id INTEGER PRIMARY KEY,
            survey_id INTEGER,
            age_group TEXT,
            gender TEXT,
            location TEXT,
            education_level TEXT,
            income_range TEXT,
            FOREIGN KEY (survey_id) REFERENCES surveys (id)
        )''')
        
        self.conn.commit()
        logger.info("✅ Database tables ready")
    
    def import_csv_file(self, file_path: str, table_name: str, mapping: Optional[Dict] = None):
        """Import data from CSV file"""
        try:
            df = pd.read_csv(file_path)
            logger.info(f"📁 Reading CSV: {file_path} ({len(df)} rows)")
            
            # Apply column mapping if provided
            if mapping:
                df = df.rename(columns=mapping)
            
            # Convert to our database format
            self._insert_dataframe(df, table_name)
            logger.info(f"✅ Imported {len(df)} records to {table_name}")
            
        except Exception as e:
            logger.error(f"❌ CSV import failed: {str(e)}")
    
    def import_excel_file(self, file_path: str, sheet_mappings: Dict[str, str]):
        """Import data from Excel file with multiple sheets"""
        try:
            excel_file = pd.ExcelFile(file_path)
            logger.info(f"📊 Reading Excel: {file_path}")
            logger.info(f"   Sheets found: {excel_file.sheet_names}")
            
            for sheet_name, table_name in sheet_mappings.items():
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    self._insert_dataframe(df, table_name)
                    logger.info(f"✅ Imported {len(df)} records from sheet '{sheet_name}' to {table_name}")
                else:
                    logger.warning(f"⚠️ Sheet '{sheet_name}' not found")
                    
        except Exception as e:
            logger.error(f"❌ Excel import failed: {str(e)}")
    
    def import_json_file(self, file_path: str, data_structure: str = "auto"):
        """Import data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"📄 Reading JSON: {file_path}")
            
            if data_structure == "auto":
                # Try to auto-detect structure
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key.lower() in ['surveys', 'survey']:
                            self._process_json_data(value, 'surveys')
                        elif key.lower() in ['responses', 'response']:
                            self._process_json_data(value, 'responses')
                        elif key.lower() in ['demographics', 'demographic']:
                            self._process_json_data(value, 'demographics')
                elif isinstance(data, list):
                    # Assume it's survey data
                    self._process_json_data(data, 'surveys')
            
            logger.info("✅ JSON import completed")
            
        except Exception as e:
            logger.error(f"❌ JSON import failed: {str(e)}")
    
    def import_sql_dump(self, file_path: str):
        """Import data from SQL dump file (PostgreSQL or MySQL format)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            logger.info(f"🗄️ Reading SQL dump: {file_path}")
            
            # Convert PostgreSQL/MySQL syntax to SQLite
            sql_content = self._convert_sql_to_sqlite(sql_content)
            
            # Split into individual statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            cursor = self.conn.cursor()
            successful = 0
            
            for stmt in statements:
                try:
                    if stmt.upper().startswith('INSERT'):
                        cursor.execute(stmt)
                        successful += 1
                except Exception as e:
                    logger.warning(f"⚠️ Skipped statement: {str(e)[:100]}...")
            
            self.conn.commit()
            logger.info(f"✅ Executed {successful} SQL statements")
            
        except Exception as e:
            logger.error(f"❌ SQL import failed: {str(e)}")
    
    def _convert_sql_to_sqlite(self, sql_content: str) -> str:
        """Convert PostgreSQL/MySQL SQL to SQLite format"""
        # Remove PostgreSQL specific syntax
        sql_content = re.sub(r'SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY', sql_content)
        sql_content = re.sub(r'AUTOINCREMENT', '', sql_content)
        sql_content = re.sub(r'DEFAULT CURRENT_TIMESTAMP', "DEFAULT CURRENT_TIMESTAMP", sql_content)
        sql_content = re.sub(r'::timestamp', '', sql_content)
        sql_content = re.sub(r'::date', '', sql_content)
        
        # Remove comments
        sql_content = re.sub(r'--.*?\n', '\n', sql_content)
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
        
        return sql_content
    
    def _process_json_data(self, data: List[Dict], table_name: str):
        """Process JSON data and insert into database"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        self._insert_dataframe(df, table_name)
        logger.info(f"✅ Imported {len(df)} records to {table_name}")
    
    def _insert_dataframe(self, df: pd.DataFrame, table_name: str):
        """Insert pandas DataFrame into database table"""
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Handle different table schemas
        if table_name == 'surveys':
            df = self._normalize_surveys_data(df)
        elif table_name == 'responses':
            df = self._normalize_responses_data(df)
        elif table_name == 'demographics':
            df = self._normalize_demographics_data(df)
        
        # Insert into database
        df.to_sql(table_name, self.conn, if_exists='append', index=False)
    
    def _normalize_surveys_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize surveys data to match our schema"""
        # Map common column variations
        column_mapping = {
            'survey_title': 'title',
            'survey_name': 'title',
            'name': 'title',
            'survey_description': 'description',
            'desc': 'description',
            'date_created': 'created_date',
            'create_date': 'created_date',
            'survey_status': 'status'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Ensure required columns exist
        if 'title' not in df.columns and len(df.columns) > 0:
            df['title'] = f"Survey {df.index + 1}"
        
        if 'status' not in df.columns:
            df['status'] = 'active'
        
        return df[['title', 'description', 'created_date', 'status']].fillna('')
    
    def _normalize_responses_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize responses data to match our schema"""
        column_mapping = {
            'survey': 'survey_id',
            'age': 'respondent_age',
            'gender': 'respondent_gender',
            'response': 'response_text',
            'answer': 'response_text',
            'score': 'rating',
            'timestamp': 'submitted_at',
            'date': 'submitted_at'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Ensure survey_id exists
        if 'survey_id' not in df.columns:
            df['survey_id'] = 1  # Default to first survey
        
        return df
    
    def _normalize_demographics_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize demographics data to match our schema"""
        column_mapping = {
            'survey': 'survey_id',
            'education': 'education_level',
            'income': 'income_range'
        }
        
        df = df.rename(columns=column_mapping)
        
        if 'survey_id' not in df.columns:
            df['survey_id'] = 1
        
        return df
    
    def import_from_directory(self, directory_path: str):
        """Auto-import all supported files from a directory"""
        logger.info(f"📁 Scanning directory: {directory_path}")
        
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            if filename.lower().endswith('.csv'):
                # Try to guess table name from filename
                if 'survey' in filename.lower():
                    self.import_csv_file(file_path, 'surveys')
                elif 'response' in filename.lower():
                    self.import_csv_file(file_path, 'responses')
                elif 'demographic' in filename.lower():
                    self.import_csv_file(file_path, 'demographics')
                else:
                    logger.info(f"📄 Found CSV: {filename} (specify table manually)")
            
            elif filename.lower().endswith(('.xlsx', '.xls')):
                # Default sheet mapping
                sheet_mappings = {
                    'surveys': 'surveys',
                    'responses': 'responses', 
                    'demographics': 'demographics',
                    'Survey': 'surveys',
                    'Response': 'responses',
                    'Demographics': 'demographics'
                }
                self.import_excel_file(file_path, sheet_mappings)
            
            elif filename.lower().endswith('.json'):
                self.import_json_file(file_path)
            
            elif filename.lower().endswith('.sql'):
                self.import_sql_dump(file_path)
    
    def get_data_summary(self):
        """Get summary of imported data"""
        cursor = self.conn.cursor()
        
        summary = {}
        for table in ['surveys', 'responses', 'demographics']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            summary[table] = count
        
        return summary
    
    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    """Interactive data import"""
    print("🔄 Universal Survey Data Importer")
    print("=" * 50)
    
    importer = SurveyDataImporter()
    
    print("""
📥 Supported formats:
1. CSV files (.csv)
2. Excel files (.xlsx, .xls)
3. JSON files (.json)
4. SQL dump files (.sql)
5. Entire directory (auto-detect)

💡 Just drag & drop your files or provide the path!
    """)
    
    while True:
        choice = input("\nWhat would you like to import? (file path, directory path, or 'quit'): ").strip()
        
        if choice.lower() in ['quit', 'exit', 'q']:
            break
        
        if not os.path.exists(choice):
            print(f"❌ Path not found: {choice}")
            continue
        
        try:
            if os.path.isdir(choice):
                importer.import_from_directory(choice)
            elif choice.lower().endswith('.csv'):
                table = input("Which table? (surveys/responses/demographics): ").strip()
                importer.import_csv_file(choice, table)
            elif choice.lower().endswith(('.xlsx', '.xls')):
                sheet_mappings = {
                    'surveys': 'surveys',
                    'responses': 'responses',
                    'demographics': 'demographics'
                }
                importer.import_excel_file(choice, sheet_mappings)
            elif choice.lower().endswith('.json'):
                importer.import_json_file(choice)
            elif choice.lower().endswith('.sql'):
                importer.import_sql_dump(choice)
            else:
                print("❌ Unsupported file format")
                continue
            
            # Show summary
            summary = importer.get_data_summary()
            print(f"\n📊 Current data summary:")
            for table, count in summary.items():
                print(f"   {table}: {count} records")
        
        except Exception as e:
            print(f"❌ Import failed: {str(e)}")
    
    importer.close()
    print("\n✅ Import session completed!")

if __name__ == "__main__":
    main()
