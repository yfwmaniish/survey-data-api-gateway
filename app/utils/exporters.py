import csv
import json
import io
from typing import List, Dict, Any, Optional
import pandas as pd
from fastapi.responses import StreamingResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataExporter:
    """Advanced data export utilities"""
    
    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], filename: Optional[str] = None) -> StreamingResponse:
        """Export query results to CSV format"""
        if not data:
            # Return empty CSV
            output = io.StringIO()
            output.write("No data available\n")
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename or 'export.csv'}"}
            )
        
        # Create StringIO buffer
        output = io.StringIO()
        
        # Get field names from first row
        fieldnames = list(data[0].keys())
        
        # Create CSV writer
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for row in data:
            # Handle None values and convert to strings
            cleaned_row = {}
            for key, value in row.items():
                if value is None:
                    cleaned_row[key] = ""
                elif isinstance(value, (dict, list)):
                    cleaned_row[key] = json.dumps(value)
                else:
                    cleaned_row[key] = str(value)
            writer.writerow(cleaned_row)
        
        # Get CSV content
        output.seek(0)
        csv_content = output.getvalue()
        
        # Create response
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename or 'export.csv'}"}
        )
    
    @staticmethod
    def export_to_excel(data: List[Dict[str, Any]], filename: Optional[str] = None) -> StreamingResponse:
        """Export query results to Excel format"""
        try:
            if not data:
                # Create empty DataFrame
                df = pd.DataFrame({"Message": ["No data available"]})
            else:
                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                # Handle complex data types
                for col in df.columns:
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            
            # Create Excel file in memory
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Query Results', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['Export Date', 'Total Rows', 'Columns'],
                    'Value': [
                        datetime.utcnow().isoformat(),
                        len(data),
                        len(data[0].keys()) if data else 0
                    ]
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename or 'export.xlsx'}"}
            )
            
        except Exception as e:
            logger.error(f"Excel export error: {str(e)}")
            # Fallback to CSV
            return DataExporter.export_to_csv(data, filename.replace('.xlsx', '.csv') if filename else 'export.csv')
    
    @staticmethod
    def export_to_json(data: List[Dict[str, Any]], filename: Optional[str] = None, pretty: bool = True) -> StreamingResponse:
        """Export query results to JSON format"""
        # Create export metadata
        export_data = {
            "metadata": {
                "export_date": datetime.utcnow().isoformat(),
                "total_rows": len(data),
                "columns": list(data[0].keys()) if data else []
            },
            "data": data
        }
        
        # Convert to JSON
        if pretty:
            json_content = json.dumps(export_data, indent=2, default=str)
        else:
            json_content = json.dumps(export_data, default=str)
        
        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename or 'export.json'}"}
        )
    
    @staticmethod
    def export_to_parquet(data: List[Dict[str, Any]], filename: Optional[str] = None) -> StreamingResponse:
        """Export query results to Parquet format (compressed, efficient)"""
        try:
            if not data:
                # Create empty DataFrame
                df = pd.DataFrame({"Message": ["No data available"]})
            else:
                df = pd.DataFrame(data)
            
            # Create Parquet file in memory
            output = io.BytesIO()
            df.to_parquet(output, engine='pyarrow', compression='snappy')
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue()),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename or 'export.parquet'}"}
            )
            
        except Exception as e:
            logger.error(f"Parquet export error: {str(e)}")
            # Fallback to JSON
            return DataExporter.export_to_json(data, filename.replace('.parquet', '.json') if filename else 'export.json')

class StreamingExporter:
    """For large datasets that need to be streamed"""
    
    @staticmethod
    def stream_csv(data_generator, filename: Optional[str] = None):
        """Stream large CSV exports"""
        def generate():
            # Start with header
            first_row = True
            for batch in data_generator:
                if not batch:
                    continue
                    
                output = io.StringIO()
                fieldnames = list(batch[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                if first_row:
                    writer.writeheader()
                    first_row = False
                
                for row in batch:
                    cleaned_row = {}
                    for key, value in row.items():
                        if value is None:
                            cleaned_row[key] = ""
                        elif isinstance(value, (dict, list)):
                            cleaned_row[key] = json.dumps(value)
                        else:
                            cleaned_row[key] = str(value)
                    writer.writerow(cleaned_row)
                
                yield output.getvalue().encode('utf-8')
                output.close()
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename or 'large_export.csv'}"}
        )
    
    @staticmethod
    def stream_json(data_generator, filename: Optional[str] = None):
        """Stream large JSON exports"""
        def generate():
            yield b'{"data": ['
            first_batch = True
            
            for batch in data_generator:
                if not batch:
                    continue
                
                if not first_batch:
                    yield b','
                
                batch_json = json.dumps(batch, default=str)[1:-1]  # Remove brackets
                yield batch_json.encode('utf-8')
                first_batch = False
            
            # Add metadata
            metadata = {
                "export_date": datetime.utcnow().isoformat(),
                "export_type": "streaming"
            }
            
            yield b'], "metadata": '
            yield json.dumps(metadata, default=str).encode('utf-8')
            yield b'}'
        
        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename or 'large_export.json'}"}
        )

def get_export_format_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available export formats"""
    return {
        "csv": {
            "name": "Comma Separated Values",
            "extension": ".csv",
            "mime_type": "text/csv",
            "description": "Standard CSV format, compatible with Excel and most tools",
            "best_for": "Small to medium datasets, spreadsheet import"
        },
        "excel": {
            "name": "Microsoft Excel",
            "extension": ".xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "description": "Excel format with multiple sheets and formatting",
            "best_for": "Business reports, presentations, formatted data"
        },
        "json": {
            "name": "JavaScript Object Notation",
            "extension": ".json",
            "mime_type": "application/json",
            "description": "Structured JSON format with metadata",
            "best_for": "API integration, web applications, structured data"
        },
        "parquet": {
            "name": "Apache Parquet",
            "extension": ".parquet",
            "mime_type": "application/octet-stream",
            "description": "Compressed columnar format, very efficient",
            "best_for": "Large datasets, data analytics, big data processing"
        }
    }
